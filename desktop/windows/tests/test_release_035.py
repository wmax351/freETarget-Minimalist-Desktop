import pathlib,unittest
from app.version import APP_VERSION,SCHEMA_VERSION
ROOT=pathlib.Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/assets/index.html').read_text(encoding='utf-8')
class Release035Tests(unittest.TestCase):
 def test_version_and_data_compatibility(self):
  self.assertEqual(APP_VERSION,'0.3.12-beta.1')
  self.assertEqual(SCHEMA_VERSION,1)
  self.assertIn("const DASHBOARD_LAYOUT_KEY='ft-dashboard-widgets-v1'",HTML)
 def test_edit_widgets_label(self):
  self.assertIn('widgetCustomizeText',HTML)
  self.assertIn("customize.title='Edit Widgets'",HTML)
  self.assertIn("$('themeBtn').before(customize)",HTML)
  self.assertIn("customize.setAttribute('aria-label',label)",HTML)
 def test_all_dashboard_widgets_collapsible(self):
  self.assertIn('function ensureDashboardWidgetCollapsible(panel)',HTML)
  self.assertIn("grid.querySelectorAll('[data-widget]').forEach(ensureDashboardWidgetCollapsible)",HTML)
  self.assertIn("panel.classList.add('collapsible')",HTML)
  self.assertIn("const key='ft-panel-collapsed-'+panel.dataset.panel",HTML)
  self.assertIn("panel.className='card collapsible dashboardNewWidget'",HTML)
 def test_padding(self):
  self.assertIn('.dashboardWidgets>.dashboardNewWidget{padding:0!important}',HTML)
  self.assertIn('.dashboardWidgets .dashboardNewWidget>.collapseBody{padding:0 10px 10px}',HTML)
 def test_removed_unneeded_session_detail_fields(self):
  self.assertIn("const fields=[['Session',sessionName()],['Structure',structure]];",HTML)
  self.assertNotIn("const fields=[['Shooter',meta.name||'Guest']",HTML)
  self.assertNotIn("const gunText=gun?",HTML)
if __name__=='__main__':unittest.main()
