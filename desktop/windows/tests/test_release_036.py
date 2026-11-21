"""Release 0.3.6 cross-platform static regression checks."""
import pathlib, unittest
from app.version import APP_VERSION, SCHEMA_VERSION
ROOT=pathlib.Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/assets/index.html').read_text(encoding='utf-8')
class Release036Tests(unittest.TestCase):
 def test_version_and_storage_compatibility(self):
  self.assertEqual(APP_VERSION,'0.3.12-beta.1')
  self.assertEqual(SCHEMA_VERSION,1)
  self.assertIn("const DASHBOARD_LAYOUT_KEY='ft-dashboard-widgets-v1'",HTML)
 def test_edit_widgets_toggle_and_visible_state(self):
  self.assertIn("$('widgetCustomize').addEventListener('click',toggleDashboardEditing)",HTML)
  self.assertIn("const label=T(dashboardEditing?'Done Editing':'Edit Widgets')",HTML)
  self.assertIn("customize.setAttribute('aria-pressed',String(dashboardEditing))",HTML)
  self.assertIn("if(left)left.scrollTop=0",HTML)
  self.assertIn(".dashboardEditToolbar{position:sticky;top:0;z-index:5}",HTML)
 def test_previous_target_initial_and_resize(self):
  self.assertIn('function syncPreviousTargetSize()',HTML)
  self.assertIn('function initPreviousTargetSizing()',HTML)
  self.assertIn("observer.observe($('dashboardWidgets'))",HTML)
  self.assertIn("window.addEventListener('resize',schedulePreviousTargetSize)",HTML)
  self.assertIn("target.style.setProperty('height',side,'important')",HTML)
  self.assertIn("initDashboardWidgets();initPreviousTargetSizing()",HTML)
  self.assertIn('.dashboardWidgets>.previousCard{height:auto!important',HTML)
 def test_mac_logo_caption_absent(self):
  if (ROOT/'BUILD_MAC.command').exists():
   self.assertNotIn('class="minimalistCaption"',HTML)
   self.assertNotIn('Designed for the freETarget Minimalist build',HTML)
if __name__=='__main__':unittest.main()
