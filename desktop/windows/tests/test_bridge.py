import importlib.util
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
import freetarget_bridge as b

ECHO_642 = (
    b'{"NAME":"FET-TARGET","NAME_ID":0,"LED_BRIGHT":50,"PAPER_TIME":500,'
    b'"SENSOR":232.00,"STEP_COUNT":0,"STEP_RE_TO_SLEEP":0.00,'
    b'"NOTE":"literal \\"DIP\\": \\"--CD\\" and *** STATUS ***",'
    b'"DIP":"--CD"\n"VERSION":"6.4.2 July 19, 2026","OTA BUILD":60301,'
    b'"LOCKED":"No" "PS_VERSION":17,"BD_REV":6.0.0 "SPLINE FIT":"Yes",}'
)

def reset():
    b.state.update(connected=False,connecting=False,message='Disconnected',events=[],next_id=1,
                   generation=10,resource=None,cancel=None,config={'method':'tcp'},identity=None,
                   bytes_received=0,raw_packets=0,parse_errors=0,successful_config=None,
                   target_settings=None,settings_event_id=0,connection_epoch=0)

def request(path,body=None):
    h=b.Handler.__new__(b.Handler);h.path=path;h.wfile=io.BytesIO();raw=json.dumps(body).encode() if body is not None else b''
    h.rfile=io.BytesIO(raw);h.headers={'Content-Length':str(len(raw))};h.send_response=lambda status:setattr(h,'status',status)
    h.send_header=lambda *args:None;h.end_headers=lambda:None
    if body is None:h.do_GET()
    else:h.do_POST()
    return h.status,json.loads(h.wfile.getvalue())

class BridgeTests(unittest.TestCase):
    def setUp(self):reset()
    def test_stream_shared_framing(self):
        raw=b'trace before JSON\n{"shot":1,"x":-14.35,"y":-5.54,"V_REF":1.7, ,"T":22, ,"name":"a,,{b}"}\r\n{"settings":{"nested":"ok"}}\n{"shot":2,"miss":1}'
        stream=b.PacketStream(10)
        for cut in range(0,len(raw),7):stream.feed(raw[cut:cut+7])
        shots=[e for e in b.state['events'] if e['type']=='shot'];self.assertEqual(len(shots),2)
        self.assertEqual(shots[0]['x'],-14.35);self.assertEqual(shots[0]['raw']['name'],'a,,{b}')
        self.assertTrue(shots[1]['miss']);self.assertEqual(shots[1]['x'],0);self.assertEqual(b.state['raw_packets'],3)
        self.assertEqual(b.state['bytes_received'],len(raw))
    def test_malformed_and_stale_stream(self):
        s=b.PacketStream(10);s.feed(b'{invalid}{"shot":1,"x":2,"y":3}')
        self.assertEqual(b.state['parse_errors'],1);self.assertEqual(len([e for e in b.state['events'] if e['type']=='shot']),1)
        before=b.state['bytes_received'];b.state['generation']=11;s.feed(b'{"shot":2,"x":2,"y":3}')
        self.assertEqual(b.state['bytes_received'],before)
    def test_nonfinite_packet_does_not_break_event_polling(self):
        b.PacketStream(10).feed(b'{"shot":1,"x":NaN,"y":0}{"shot":2,"x":1,"y":2}')
        code,data=request('/api/events?after=0');self.assertEqual(code,200)
        self.assertEqual(data['parse_errors'],1)
        self.assertEqual(len([e for e in data['events'] if e['type']=='shot']),1)

    def test_serial_ports_missing_dependency_and_validation(self):
        with patch.object(b,'serial',None),patch.object(b,'list_ports',None):
            code,data=request('/api/serial-ports');self.assertEqual(code,200);self.assertFalse(data['available'])
            code,data=request('/api/connect',{'method':'serial','serial_port':'COM3'})
            self.assertEqual(code,400);self.assertIn('INSTALL_USB_SUPPORT',data['error'])
            self.assertEqual(b.validate_config({'host':'192.168.86.35','port':1090})['method'],'tcp')
        with patch.object(b,'serial',object()):
            for port in ['COM3','COM12','/dev/cu.usbserial-12','/dev/ttyUSB0']:
                self.assertEqual(b.validate_config({'method':'serial','serial_port':port})['baudrate'],115200)
            for port in ['https://not-local','file.txt','COM0','']:
                with self.assertRaises(ValueError):b.validate_config({'method':'serial','serial_port':port})
    def test_clear_log_preserves_unpolled_shots(self):
        b.PacketStream(10).feed(b'{"shot":1,"x":1,"y":2}')
        code,data=request('/api/clear-diagnostics',{});self.assertEqual(code,200)
        code,data=request('/api/events?after=0');self.assertEqual(len(data['events']),1)
        self.assertEqual(data['events'][0]['type'],'shot');self.assertEqual(data['raw_packets'],0)
        self.assertEqual(data['bytes_received'],0)
    def test_usb_unplug_reconnect_to_new_port_and_cancel(self):
        class Cancel:
            stopped=False
            def is_set(self):return self.stopped
            def set(self):self.stopped=True
            def wait(self,seconds):return self.stopped
        cancel=Cancel();opened=[];current_ports=[dict(device='COM3',description='Target',serial_number='ABC',vid=1,pid=2,location='A')]
        class SerialPort:
            def __init__(self,**kwargs):
                self.settings=kwargs;self.port=None;self.dtr=True;self.rts=True;self.closed=False;self.parts=[]
            def open(self):
                assert not self.dtr and not self.rts
                opened.append(self)
                self.parts=([b'{"shot":1,"x":',b'4,"y":5}'] if len(opened)==1 else [b'{"shot":2,"miss":1}'])
            @property
            def in_waiting(self):return len(self.parts[0]) if self.parts else 1
            def read(self,n):
                if self.parts:return self.parts.pop(0)
                if len(opened)==1:
                    current_ports[0]={**current_ports[0],'device':'COM7'}
                    raise OSError('unplugged')
                cancel.set();return b''
            def close(self):self.closed=True
        config=dict(method='serial',serial_port='COM3',baudrate=115200,auto_reconnect=True)
        b.state.update(config=config,cancel=cancel)
        with patch.object(b,'serial',SimpleNamespace(Serial=SerialPort)),patch.object(b,'serial_ports',lambda:current_ports):
            b.read_connection(config,10,cancel)
        self.assertEqual([p.port for p in opened],['COM3','COM7']);self.assertTrue(all(p.closed for p in opened))
        self.assertEqual(b.state['successful_config']['serial_port'],'COM7')
        self.assertEqual(len([e for e in b.state['events'] if e['type']=='shot']),2)
        self.assertTrue(all(e['transport']=='serial' for e in b.state['events'] if e['type']=='shot'))
        self.assertTrue(all(p.settings['bytesize']==8 and p.settings['parity']=='N' and p.settings['stopbits']==1 for p in opened))
        b.stop_connection();self.assertFalse(b.state['connected']);self.assertFalse(b.state['connecting'])
    def test_usb_no_reconnect_and_ambiguous_identity(self):
        class BadPort:
            def __init__(self,**kwargs):pass
            def open(self):raise OSError('not available')
            def close(self):pass
        cancel=b.threading.Event();config=dict(method='serial',serial_port='COM3',baudrate=115200,auto_reconnect=False)
        b.state['config']=config
        with patch.object(b,'serial',SimpleNamespace(Serial=BadPort)),patch.object(b,'serial_ports',lambda:[]):b.read_connection(config,10,cancel)
        self.assertFalse(b.state['connecting']);self.assertFalse(b.state['connected'])
        identity=dict(serial_number='same',vid=1,pid=2)
        with patch.object(b,'serial_ports',lambda:[dict(identity,device='COM4'),dict(identity,device='COM5')]):
            self.assertIsNone(b.choose_serial_port(config,identity))
    def test_tcp_still_uses_the_same_stream(self):
        cancel=b.threading.Event()
        class Sock:
            def settimeout(self,n):pass
            def recv(self,n):
                cancel.set();return b'{"shot":3,"x":-1,"y":2}'
            def close(self):pass
        config=dict(method='tcp',host='192.168.86.35',port=1090);b.state.update(config=config,cancel=cancel)
        with patch.object(b.socket,'create_connection',return_value=Sock()):b.read_connection(config,10,cancel)
        shot=next(e for e in b.state['events'] if e['type']=='shot');self.assertEqual(shot['transport'],'tcp');self.assertEqual(shot['x'],-1)

    def test_642_score_and_echo_packets(self):
        stream=b.PacketStream(10)
        raw=(b'{{{{{"shot":3,"miss":0,"session_type":1,"time":123,"time_to_go":0,'
             b'"x":1.25,"y":-2.5,"elapsed_time":42s}')
        for offset in range(0,len(raw),3):stream.feed(raw[offset:offset+3])
        shot=next(e for e in b.state['events'] if e['type']=='shot')
        self.assertEqual((shot['count'],shot['x'],shot['y']),(3,1.25,-2.5))
        self.assertEqual(shot['raw']['elapsed_time'],'42s')

        echo=(b'{\r\n"NAME": "FET-TARGET", "NAME_ID": 0, "LED_BRIGHT": 50, '
              b'"SENSOR": 232.00, "PAPER_TIME": 500,\r\n*** STATUS ***\r\n'
              b'"WiFi_IP_ADDRESS": "192.168.10.9", "VERSION": "6.4.2 July 19, 2026",\r\n}')
        for offset in range(0,len(echo),5):stream.feed(echo[offset:offset+5])
        self.assertEqual(b.state['target_settings']['VERSION'],'6.4.2 July 19, 2026')
        self.assertEqual(b.state['target_settings']['NAME_ID'],0)
        self.assertEqual(b.state['parse_errors'],0)

    def setup_command_target(self,method='tcp'):
        b.state.update(connection_epoch=7,connected=True,connecting=False,config={'method':method},target_settings=None,settings_event_id=0)
        values={k:0 for k in b.TARGET_PROTOCOL['fields']};values.update(NAME_ID=0,LED_BRIGHT=70,SENSOR=230,PAPER_TIME=50,VERSION='4.2.8 WiFi Test 1')
        sent=[]
        class Device:
            def sendall(self,data):
                sent.append(data);command=json.loads(data)
                values.update({k:v for k,v in command.items() if k!='ECHO'})
                if 'ECHO' in command:b.PacketStream(b.state['generation']).feed(json.dumps(values).encode())
            def close(self):pass
        device=Device();b.state['resource']=device
        return values,sent,device
    def test_command_read_apply_and_firmware_buffer(self):
        values,sent,device=self.setup_command_target();result=b.get_target_settings();self.assertEqual(result['settings']['SENSOR'],230)
        self.assertEqual(sent[0],b'{"ECHO":0}\n')
        changes={k:120 for k in b.TARGET_PROTOCOL['fields']};changes.update(NAME_ID=2,LED_BRIGHT=60,SENSOR=245.5)
        result=b.apply_target_settings(changes,7,True);self.assertTrue(result['verified'])
        for key,value in changes.items():self.assertEqual(result['settings'][key],value)
        self.assertTrue(all(len(w)<=220 for w in sent));self.assertGreaterEqual(len(sent),3)

    def test_question_status_command_uses_firmware_echo(self):
        _,sent,_=self.setup_command_target()
        b.send_command('?',7)
        self.assertEqual(sent,[b'{"ECHO":0}\n'])

    def test_642_settings_query_reads_echo_status_response(self):
        echo=(b'{\r\n"NAME": "FET-TARGET", "NAME_ID": 0, "LED_BRIGHT": 50, '
              b'"SENSOR": 232.00, "PAPER_TIME": 500,\r\n*** STATUS ***\r\n'
              b'"WiFi_IP_ADDRESS": "192.168.10.9", "VERSION": "6.4.2 July 19, 2026",\r\n}')
        sent=[]
        class Device:
            def sendall(self,data):
                sent.append(data)
                b.PacketStream(b.state['generation']).feed(echo)
        b.state.update(connection_epoch=7,connected=True,config={'method':'tcp'},resource=Device(),
                       target_settings=None,settings_event_id=0)
        result=b.get_target_settings()
        self.assertEqual(sent,[b'{"ECHO":0}\n'])
        self.assertEqual(result['settings']['VERSION'],'6.4.2 July 19, 2026')

    def test_642_recorded_echo_format_and_partial_settings(self):
        stream=b.PacketStream(10)
        for offset in range(0,len(ECHO_642),7):stream.feed(ECHO_642[offset:offset+7])
        settings=b.state['target_settings']
        self.assertEqual(settings['PAPER_TIME'],500)
        self.assertEqual(settings['BD_REV'],'6.0.0')
        self.assertEqual(settings['NOTE'],'literal "DIP": "--CD" and *** STATUS ***')
        self.assertNotIn('STEP_TIME',settings)
        self.assertEqual(b.state['parse_errors'],0)

    def test_642_rejects_other_malformed_packets_and_recovers(self):
        stream=b.PacketStream(10)
        stream.feed(ECHO_642.replace(b'"NAME_ID":0,',b'"NAME_ID":0 ')+b'{"shot":4,"x":1,"y":2}')
        self.assertEqual(b.state['parse_errors'],1)
        self.assertIsNone(b.state.get('target_settings'))
        self.assertTrue(any(event['type']=='shot' for event in b.state['events']))

    def test_642_firmware_status_marker_duplicate_serial_and_hex(self):
        raw=ECHO_642.replace(b'"DIP":',b'"SN":123,\n*** STATUS ***\n"SN":123 "TRACE":0,"CONNECTION_LIST":0A,"DIP":')
        result=b.parse_target_packet(raw.decode())
        self.assertEqual((result['SN'],result['TRACE'],result['CONNECTION_LIST']),(123,0,'0A'))
        with self.assertRaises(ValueError):
            b.parse_target_packet(raw.replace(b'"SN":123 "TRACE"',b'"SN":124 "TRACE"').decode())

    def test_normalization_preserves_quoted_status_and_punctuation(self):
        packet={'note':'*** STATUS *** ,} "elapsed_time":42s}'}
        raw=json.dumps(packet)[:-1]+',}'
        self.assertEqual(b.parse_target_packet(raw),packet)

    def test_invalid_reported_field_is_not_available_for_editing(self):
        raw=ECHO_642.replace(b'"LED_BRIGHT":50',b'"LED_BRIGHT":"garbled"')
        b.PacketStream(10).feed(raw)
        self.assertNotIn('LED_BRIGHT',b.state['target_settings'])
        self.assertEqual(b.state['target_settings']['SENSOR'],232)

    def test_missing_write_readback_is_not_verified_or_retried(self):
        sent=[]
        class Device:
            def sendall(self,data):
                sent.append(data)
                response=ECHO_642 if len(sent)==1 else ECHO_642.replace(b'"LED_BRIGHT":50,',b'')
                b.PacketStream(b.state['generation']).feed(response)
        b.state.update(connection_epoch=7,connected=True,config={'method':'tcp'},resource=Device(),
                       target_settings=None,settings_event_id=0)
        b.get_target_settings()
        with patch.object(b.time,'monotonic',side_effect=[0,26]):
            with self.assertRaisesRegex(ValueError,'No complete settings response'):
                b.apply_target_settings({'LED_BRIGHT':60},7,True)
        self.assertEqual(len(sent),2)

    def test_642_realistic_echo_read_and_write_readback(self):
        sent=[]
        class Device:
            def sendall(self,data):
                sent.append(data)
                command=json.loads(data)
                echo=ECHO_642.replace(b'"PAPER_TIME":500',b'"PAPER_TIME":250') if command.get('PAPER_TIME')==250 else ECHO_642
                stream=b.PacketStream(b.state['generation'])
                for offset in range(0,len(echo),9):stream.feed(echo[offset:offset+9])
        b.state.update(connection_epoch=7,connected=True,config={'method':'tcp'},resource=Device(),
                       target_settings=None,settings_event_id=0)
        self.assertEqual(b.get_target_settings()['settings']['PAPER_TIME'],500)
        with self.assertRaises(ValueError):b.apply_target_settings({'STEP_TIME':5},7,True)
        self.assertEqual(len(sent),1)
        result=b.apply_target_settings({'PAPER_TIME':250},7,True)
        self.assertTrue(result['verified'])
        self.assertEqual(result['settings']['PAPER_TIME'],250)
    def test_command_rejects_stale_unsupported_and_unconfirmed(self):
        values,sent,device=self.setup_command_target();b.get_target_settings();before=len(sent)
        for command in [{'NAME_ID':50},{'LED_BRIGHT':101}]:
            with self.assertRaises(ValueError):b.send_command(command,7,True)
        with self.assertRaises(ValueError):b.send_command({'LED_BRIGHT':50},7,False)
        with self.assertRaises(ValueError):b.send_command({'ECHO':0},999)
        with self.assertRaises(ValueError):b.apply_target_settings({'SENSOR':200},999,True)
        self.assertEqual(len(sent),before)

    def test_642_commands_and_name_ids(self):
        values,sent,_=self.setup_command_target()
        values['VERSION']='6.4.2 July 19, 2026'
        b.state['target_settings']=values
        b.send_command({'CAL':0},7,True)
        b.send_command({'X_OFFSET':1.5},7,True)
        b.send_command({'NAME_ID':99},7,True)
        with self.assertRaises(ValueError):b.send_command({'NAME_ID':30},7,True)
        self.assertEqual([json.loads(item) for item in sent],[
            {'CAL':0},{'X_OFFSET':1.5},{'NAME_ID':99}])
    def test_command_partial_serial_write_and_redacted_password(self):
        values,sent,device=self.setup_command_target('serial');parts=[]
        class Serial:
            def write(self,data):parts.append(data[:3]);return min(3,len(data))
        b.state['resource']=Serial();b.send_command({'WIFI_PWD':'plain-pass'},7,True)
        self.assertEqual(json.loads(b''.join(parts)),{'WIFI_PWD':'plain-pass'})
        event=next(e for e in b.state['events'] if e['type']=='sent');self.assertNotIn('plain-pass',event['text']);self.assertIn('********',event['text'])
    def test_command_failed_readback_never_repeats_write(self):
        values,sent,device=self.setup_command_target()
        class NoEcho:
            def sendall(self,data):sent.append(data)
        b.state['resource']=NoEcho()
        with patch.object(b.time,'monotonic',side_effect=[0,26]):
            with self.assertRaises(ValueError):b.get_target_settings()
        self.assertEqual(len(sent),1)
    def test_command_write_error_no_automatic_retry(self):
        values,sent,device=self.setup_command_target()
        class Broken:
            def sendall(self,data):sent.append(data);raise OSError('closed')
        b.state['resource']=Broken()
        with self.assertRaises(OSError):b.send_command({'ECHO':0},7)
        self.assertEqual(len(sent),1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
