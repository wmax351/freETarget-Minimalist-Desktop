package designs.struve.freetarget.android;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbManager;
import android.net.ConnectivityManager;
import android.os.Handler;
import android.os.Looper;
import com.hoho.android.usbserial.driver.UsbSerialDriver;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import com.hoho.android.usbserial.driver.UsbSerialProber;
import android.net.Network;
import android.net.NetworkCapabilities;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.ArrayDeque;

/** Adapts Wi-Fi and USB target streams to the existing scoring UI's event API. */
final class TargetConnection {
    private static final int MAX_EVENTS = 2048;
    private static final int MAX_QUEUE_CHARS = 2_000_000;
    static final String USB_PERMISSION = "designs.struve.freetarget.android.USB_PERMISSION";
    private final Context context;
    private final ConnectivityManager networks;
    private final UsbManager usb;
    private String method = "tcp";
    private UsbSerialPort pendingPort;
    private int pendingBaud;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ArrayDeque<Event> events = new ArrayDeque<>();
    private Socket socket;
    private long generation, nextId = 1, epoch, bytesReceived, packets, errors;
    private int queueChars;
    private boolean connected, connecting;
    private String message = "Disconnected";
    private JSONObject successfulConfig;

    private static final class Event {
        private final long id;
        private final JSONObject json;
        private final int size;

        Event(long id, JSONObject json, int size) {
            this.id = id;
            this.json = json;
            this.size = size;
        }

        long id() { return id; }
        JSONObject json() { return json; }
        int size() { return size; }
    }

    TargetConnection(Context context) {
        this.context = context.getApplicationContext();
        networks = context.getSystemService(ConnectivityManager.class);
        usb = context.getSystemService(UsbManager.class);
    }

    private static String portId(UsbSerialPort port) {
        return port.getDriver().getDevice().getDeviceName() + ":" + port.getPortNumber();
    }

    JSONObject serialPorts() throws JSONException {
        JSONArray ports = new JSONArray();
        if (usb != null) {
            for (UsbSerialDriver driver : UsbSerialProber.getDefaultProber().findAllDrivers(usb)) {
                UsbDevice device = driver.getDevice();
                for (UsbSerialPort port : driver.getPorts()) {
                    ports.put(new JSONObject().put("device", portId(port))
                            .put("description", String.format("%s · %04X:%04X · Port %d",
                                    driver.getClass().getSimpleName().replace("SerialDriver", ""),
                                    device.getVendorId(), device.getProductId(), port.getPortNumber() + 1)));
                }
            }
        }
        return new JSONObject().put("available", usb != null).put("ports", ports);
    }

    private synchronized void connectSerial(JSONObject config) {
        String selected = config.optString("serial_port");
        int baud = config.optInt("baudrate", 115200);
        if (usb == null || baud < 300 || baud > 2000000) {
            throw new IllegalArgumentException("Check USB host support and enter a valid baud rate.");
        }
        UsbSerialPort match = null;
        for (UsbSerialDriver driver : UsbSerialProber.getDefaultProber().findAllDrivers(usb)) {
            for (UsbSerialPort port : driver.getPorts()) {
                if (portId(port).equals(selected)) match = port;
            }
        }
        if (match == null) {
            throw new IllegalArgumentException("USB target was not found. Refresh the USB device list.");
        }
        disconnect("Disconnected");
        method = "serial";
        long attempt = generation;
        connecting = true;
        pendingPort = match;
        pendingBaud = baud;
        try {
            if (usb.hasPermission(match.getDriver().getDevice())) {
                usbPermissionResult(attempt);
            } else {
                message = "Waiting for Android USB permission…";
                Intent intent = new Intent(USB_PERMISSION).setPackage(context.getPackageName())
                        .putExtra("attempt", attempt);
                PendingIntent permission = PendingIntent.getBroadcast(context, (int) attempt, intent,
                        PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_ONE_SHOT);
                usb.requestPermission(match.getDriver().getDevice(), permission);
                main.postDelayed(() -> {
                    synchronized (TargetConnection.this) {
                        if (attempt == generation && pendingPort != null)
                            disconnect("USB permission request expired. Try connecting again.");
                    }
                }, 120000);
            }
        } catch (RuntimeException error) {
            disconnect("Could not request USB access.");
            throw new IllegalArgumentException("Could not request USB access.", error);
        }
    }

    synchronized void usbPermissionResult(long attempt) {
        if (attempt != generation || pendingPort == null) return;
        UsbSerialPort port = pendingPort;
        pendingPort = null;
        int baud = pendingBaud;
        if (!usb.hasPermission(port.getDriver().getDevice())) {
            disconnect("USB access was denied or the device was removed.");
            return;
        }
        message = "Opening USB target…";
        new Thread(() -> receiveSerial(attempt, port, baud), "freETarget USB").start();
    }

    private void receiveSerial(long attempt, UsbSerialPort port, int baud) {
        try {
            if (!isCurrent(attempt)) return;
            UsbDeviceConnection connection = usb.openDevice(port.getDriver().getDevice());
            if (connection == null) throw new IOException("Could not open USB device.");
            try {
                port.open(connection);
                port.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
                JSONObject config = new JSONObject().put("method", "serial")
                        .put("serial_port", portId(port)).put("baudrate", baud);
                if (markConnected(attempt, config, "USB/Serial connected")) {
                    readPackets(attempt, buffer -> port.read(buffer, 250));
                }
            } finally {
                try {
                    if (port.isOpen()) port.close();
                } finally {
                    connection.close();
                }
            }
            finish(attempt, "USB target disconnected.");
        } catch (IOException | JSONException | RuntimeException error) {
            finish(attempt, "USB connection ended: " + error.getMessage());
        }
    }

    synchronized void connect(JSONObject config) throws JSONException {
        if ("serial".equals(config.optString("method"))) {
            connectSerial(config);
            return;
        }
        String host = config.optString("host").trim();
        int port = config.optInt("port", -1);
        if (!"tcp".equals(config.optString("method")) || !host.matches("[a-zA-Z0-9.:_%\\-]{1,253}")
                || port < 1 || port > 65535) {
            throw new IllegalArgumentException("Enter the target Wi-Fi address and a valid TCP port.");
        }
        disconnect("Disconnected");
        long attempt = generation;
        connecting = true;
        method = "tcp";
        message = "Connecting to target…";
        JSONObject saved = new JSONObject().put("method", "tcp").put("host", host).put("port", port);
        new Thread(() -> receive(attempt, host, port, saved), "freETarget Wi-Fi").start();
    }

    private Network wifiNetwork() {
        for (Network network : networks.getAllNetworks()) {
            NetworkCapabilities capabilities = networks.getNetworkCapabilities(network);
            if (capabilities != null && capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return network;
        }
        return null;
    }

    private void receive(long attempt, String host, int port, JSONObject config) {
        try (Socket candidate = new Socket()) {
            synchronized (this) {
                if (attempt != generation) return;
                socket = candidate;
            }
            Network network = wifiNetwork();
            if (network == null) throw new IOException("Join the target’s Wi-Fi network or the same local network.");
            network.bindSocket(candidate);
            InetAddress address = network.getByName(host);
            candidate.connect(new InetSocketAddress(address, port), 8000);
            if (!markConnected(attempt, config, "Wi-Fi/TCP connected")) return;
            InputStream input = candidate.getInputStream();
            readPackets(attempt, input::read);
            finish(attempt, "Target closed the connection. Reconnect when ready.");
        } catch (IOException | SecurityException error) {
            finish(attempt, "Wi-Fi connection ended: " + error.getMessage());
        }
    }

    private synchronized boolean isCurrent(long attempt) {
        return attempt == generation;
    }

    private synchronized boolean markConnected(long attempt, JSONObject config, String status) {
        if (!isCurrent(attempt)) return false;
        connected = true;
        connecting = false;
        message = status;
        successfulConfig = config;
        epoch++;
        return true;
    }

    @FunctionalInterface
    private interface PacketReader {
        int read(byte[] buffer) throws IOException;
    }

    private void readPackets(long attempt, PacketReader reader) throws IOException {
        PacketFramer framer = new PacketFramer();
        byte[] buffer = new byte[8192];
        while (isCurrent(attempt)) {
            int length = reader.read(buffer);
            if (length < 0) return;
            if (length == 0) continue;
            synchronized (this) {
                if (!isCurrent(attempt)) return;
                bytesReceived += length;
                framer.feed(buffer, length, packet -> {
                    if (isCurrent(attempt)) consume(packet);
                }, () -> { if (isCurrent(attempt)) errors++; });
            }
        }
    }

    private synchronized void finish(long attempt, String reason) {
        if (attempt == generation) disconnect(reason);
    }

    synchronized void disconnect(String reason) {
        generation++;
        pendingPort = null;
        try {
            if (socket != null) socket.close();
        } catch (IOException ignored) {
            // Closing is best-effort. Generation checks discard obsolete callbacks.
        }
        socket = null;
        connected = false;
        connecting = false;
        message = reason;
    }

    private void consume(String text) {
        try {
            JSONObject packet = new JSONObject(text);
            packets++;
            boolean miss = packet.optInt("miss", 0) == 1;
            double count = packet.optDouble("shot");
            double x = packet.optDouble("x", miss ? 0 : Double.NaN);
            double y = packet.optDouble("y", miss ? 0 : Double.NaN);
            JSONObject event = new JSONObject();
            if (Double.isFinite(count) && count >= 0 && count <= Integer.MAX_VALUE
                    && Double.isFinite(x) && Double.isFinite(y)) {
                event.put("type", "shot").put("count", (int) count).put("x", x)
                        .put("y", y).put("miss", miss).put("transport", method).put("raw", packet);
            } else {
                event.put("type", "message").put("data", packet);
            }
            if (events.size() >= MAX_EVENTS || queueChars + text.length() > MAX_QUEUE_CHARS) {
                disconnect("The event buffer is full. Review the current result before reconnecting.");
                return;
            }
            event.put("id", nextId);
            events.add(new Event(nextId++, event, text.length()));
            queueChars += text.length();
        } catch (JSONException error) {
            errors++;
        }
    }

    synchronized JSONObject poll(long after) throws JSONException {
        while (!events.isEmpty() && events.peek().id() <= after) queueChars -= events.remove().size();
        JSONArray batch = new JSONArray();
        for (Event event : events) batch.put(event.json());
        return new JSONObject().put("connected", connected).put("connecting", connecting)
                .put("message", message).put("method", method).put("events", batch)
                .put("latest", nextId - 1).put("connection_epoch", epoch)
                .put("bytes_received", bytesReceived).put("raw_packets", packets)
                .put("parse_errors", errors).put("successful_config", successfulConfig == null
                        ? JSONObject.NULL : successfulConfig);
    }

    synchronized JSONObject clear() throws JSONException {
        bytesReceived = packets = errors = 0;
        return new JSONObject().put("latest", nextId - 1);
    }
}
