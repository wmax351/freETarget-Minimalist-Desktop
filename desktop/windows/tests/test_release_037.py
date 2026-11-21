"""0.3.7 cross-platform dashboard, logo, navigation and appearance regressions."""
from pathlib import Path
import re
import unittest
from app.version import APP_VERSION, SCHEMA_VERSION
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/assets/index.html').read_text(encoding='utf-8')
class Release037Tests(unittest.TestCase):
    def test_version_and_schema(self):
        self.assertEqual(APP_VERSION,'0.3.12-beta.1')
        self.assertEqual(SCHEMA_VERSION,1)
        self.assertIn("const DASHBOARD_LAYOUT_KEY='ft-dashboard-widgets-v1'",HTML)
    def test_all_widgets_visible_in_order(self):
        match=re.search(r'const DASHBOARD_WIDGETS=\[(.*?)\];',HTML,re.S)
        self.assertIsNotNone(match)
        specs=re.findall(r"\{id:'([^']+)',name:'[^']+',sizes:\[[^\]]+\],defaultSize:'([^']+)',visible:(true|false)\}",match.group(1))
        self.assertEqual(specs,[('scoring','large','true'),('recent','large','true'),('distribution','large','true'),('previous','large','true'),('sessionDetails','large','true'),('scorecard','large','true')])
        self.assertIn("if(!Array.isArray(raw))return fallback;",HTML)
        self.assertIn("dashboardLayout=defaultDashboardLayout();saveDashboardLayout();applyDashboardLayout()",HTML)
    def test_distribution_chart_and_subtitle(self):
        self.assertNotIn("Entire session · whole-ring counts",HTML)
        self.assertIn('grid-template-rows:repeat(10,minmax(0,1fr))',HTML)
        self.assertIn('.dashboardWidgets #distribution .barbg{height:100%;max-height:3em;',HTML)
        self.assertIn("$('distributionNote').textContent=zeros?",HTML)
    def test_previous_target_overlay_and_placeholder(self):
        self.assertIn('class="previousTargetFrame"',HTML)
        self.assertIn('class="previousControls" role="group"',HTML)
        self.assertIn('id="previousPlaceholder" role="status"',HTML)
        self.assertIn('.previousPlaceholder{position:absolute;',HTML)
        self.assertIn('bottom:9px;left:50%;transform:translateX(-50%)',HTML)
        self.assertIn("$('previousDetails').hidden=!has;$('previousPlaceholder').hidden=has",HTML)
        self.assertIn('schedulePreviousTargetSize()',HTML)
    def test_session_details_text_removed(self):
        self.assertNotIn('id="widgetCurrentStage"',HTML)
        self.assertNotIn('id="widgetProgressNote"',HTML)
        self.assertNotIn('id="widgetTimeFill"',HTML)
        self.assertIn('id="widgetProgressSegments"',HTML)
        self.assertIn('id="widgetProgressLabels"',HTML)
    def test_inline_logo_and_live_theme_colors(self):
        self.assertIn('id="brandDefaultSvg" class="brandDefaultSvg"',HTML)
        self.assertIn('fill="var(--accent)"',HTML)
        self.assertIn('fill="var(--logoShotColor, #ed8a2c)"',HTML)
        self.assertIn('fill="var(--sideText)"',HTML)
        self.assertIn("style.setProperty('--logoShotColor',targetColor('shot'))",HTML)
        self.assertIn("$('brandDefaultSvg').hidden=custom",HTML)
        self.assertIn("const active=effectiveLogo(theme)",HTML)
    def test_connect_icons(self):
        self.assertIn('id="ft-icon-plug"',HTML)
        self.assertIn('id="ft-icon-unplug"',HTML)
        self.assertIn('id="sidebarConnectIcon" href="#ft-icon-unplug"',HTML)
        self.assertIn('id="quickConnectIcon" href="#ft-icon-unplug"',HTML)
        self.assertIn("liveConnected?'#ft-icon-plug':'#ft-icon-unplug'",HTML)
if __name__=='__main__':unittest.main()
