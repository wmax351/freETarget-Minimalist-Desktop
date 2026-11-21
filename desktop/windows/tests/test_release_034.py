"""Static regression guards for the 0.3.4 Live Scoring layout refinements."""
import pathlib
import unittest
from app.version import APP_VERSION,SCHEMA_VERSION

ROOT=pathlib.Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/assets/index.html').read_text(encoding='utf-8')

class Release034Tests(unittest.TestCase):
    def test_version_and_existing_storage_schema(self):
        self.assertEqual(APP_VERSION,'0.3.12-beta.1')
        self.assertEqual(SCHEMA_VERSION,1)
    def test_footer_customize_button_and_aria_label(self):
        self.assertIn("$('themeBtn').before(customize)",HTML)
        self.assertIn("customize.id='widgetCustomize'",HTML)
        self.assertIn("customize.setAttribute('aria-label'",HTML)
        self.assertIn("customize.hidden=screen!=='Score'",HTML)
        self.assertIn("customize.setAttribute('aria-pressed',String(dashboardEditing))",HTML)
    def test_no_dashboard_fade_or_old_bottom_dock(self):
        self.assertNotIn('dashboardCustomizeDock',HTML)
        self.assertNotIn('background:linear-gradient(0deg,var(--bg) 70%,transparent)',HTML)
    def test_previous_fixed_target_layout_and_full_panel_svg(self):
        self.assertNotIn('calc(55vw - 120px)',HTML)
        self.assertIn("workspace.style.setProperty('--target-panel-size',size+'px')",HTML)
        self.assertIn('.targetWrap #targetSvg{width:100%!important;height:100%!important;max-width:100%!important;max-height:100%!important;flex:none}',HTML)
    def test_internal_ready_status_is_not_rendered_under_log(self):
        self.assertIn('id="phaseStatus" class="phaseStatus" hidden aria-hidden="true"',HTML)
        self.assertIn('.sidebarControls #phaseStatus{display:none!important}',HTML)
        self.assertNotIn('id="statusFooter"',HTML)

if __name__=='__main__':unittest.main()
