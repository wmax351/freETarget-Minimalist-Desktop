"""freETarget Minimalist 0.3.2 retained feature guards."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/assets/index.html').read_text(encoding='utf-8')
class Release032Tests(unittest.TestCase):
    def test_fixed_dashboard_and_read_only_history(self):
        self.assertNotIn('id="columnDivider"',HTML)
        self.assertNotIn('divider.addEventListener',HTML)
        self.assertIn('id="historyReviewPane"',HTML)
        self.assertIn('id="savedReviewTarget"',HTML)
        self.assertIn('id="savedSeriesLabel"',HTML)
        self.assertIn("reviewSession(index,'Statistics')",HTML)
        self.assertIn('id="statisticsSessionList"',HTML)
    def test_popup_rules_and_theme_assets(self):
        self.assertIn('id="sessionPickerOverlay"',HTML)
        self.assertNotIn('id="rulesOutline"',HTML)
        for id in ('targetLightMode','targetDarkMode','logoLightMode','logoDarkMode','voicePitch'):
            self.assertIn('id="'+id+'"',HTML)
        self.assertIn('ft-custom-logo-modes-v1',HTML)
        self.assertIn('appearance.targetModes',HTML)
    def test_languages_and_version(self):
        from app.version import APP_NAME,APP_VERSION,SCHEMA_VERSION
        self.assertEqual(APP_NAME,'freETarget Minimalist')
        self.assertEqual(APP_VERSION,'0.3.12-beta.1')
        self.assertEqual(SCHEMA_VERSION,1)
        self.assertIn('data-settings-tab="languages"',HTML)
        for lang in ('hi','zh-CN','zh-TW','ja','es','de','fr','it','pt'):
            self.assertIn('value="'+lang+'"',HTML)
        self.assertIn('ft-voice-language',HTML)
    def test_light_dark_logo_validation(self):
        import json,base64
        from app.storage import validate_entry
        tiny='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO8B6YQAAAAASUVORK5CYII='
        logo={'dataURL':'data:image/png;base64,'+tiny,'name':'test.png','width':1,'height':1}
        value=json.dumps({'light':logo,'dark':None})
        self.assertEqual(validate_entry('ft-custom-logo-modes-v1',value),value)
        with self.assertRaises(ValueError):
            validate_entry('ft-custom-logo-modes-v1',json.dumps({'light':logo,'dark':{'dataURL':'javascript:evil','name':'x','width':1,'height':1}}))
if __name__=='__main__':unittest.main()
