"""0.3.8 sidebar layout, target connection anchoring, and selector regressions."""
from pathlib import Path
import unittest
from html.parser import HTMLParser
from app.version import APP_VERSION, SCHEMA_VERSION

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'app/assets/index.html').read_text(encoding='utf-8')

class SidebarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack=[]
        self.parents={}
        self.children={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag not in {'input','img','meta','link','br','hr','source'}:
            identity=attrs.get('id') or attrs.get('class') or tag
            parent=self.stack[-1] if self.stack else 'document'
            self.children.setdefault(parent,[]).append(identity)
            if attrs.get('id'):self.parents[attrs['id']]=parent
            self.stack.append(identity)
    def handle_endtag(self,tag):
        # This test only needs the known, correctly balanced sidebar fragment.
        if self.stack:self.stack.pop()

class Release038Tests(unittest.TestCase):
    def test_version_schema_and_existing_layout_storage(self):
        self.assertEqual(APP_VERSION,'0.3.12-beta.1')
        self.assertEqual(SCHEMA_VERSION,1)
        self.assertIn("const DASHBOARD_LAYOUT_KEY='ft-dashboard-widgets-v1'",HTML)
        self.assertIn('freETarget Minimalist 0.3.12</span>',HTML)
    def test_sidebar_hierarchy_and_fixed_connection(self):
        sidebar=HTML.split('<aside class="ftSidebar">',1)[1].split('<nav aria-label="Primary navigation"',1)[0]
        self.assertLess(sidebar.index('class="brandRow"'),sidebar.index('class="sidebarTopScroll"'))
        self.assertLess(sidebar.index('class="sidebarTopScroll"'),sidebar.index('class="sidebarConnection"'))
        self.assertLess(sidebar.index('class="sidebarConnection"'),len(sidebar))
        scroll=sidebar.split('class="sidebarTopScroll"',1)[1].split('class="sidebarConnection"',1)[0]
        self.assertNotIn('id="quickConnect"',scroll)
        self.assertNotIn('id="sidebarConnect"',scroll)
        fixed=sidebar.split('class="sidebarConnection"',1)[1]
        self.assertIn('id="quickConnect"',fixed)
        self.assertIn('id="sidebarConnect"',fixed)
        self.assertIn('id="sidebarSessionControls"',scroll)
        self.assertIn('aside>.sidebarTopScroll{flex:1 1 auto;min-height:0;',HTML)
        self.assertIn('aside>.sidebarConnection{display:block!important;flex:0 0 auto;',HTML)
        self.assertIn('aside>nav,.sidebarCollapsed .app>aside>nav{flex:0 0 auto;margin-top:0!important;',HTML)
    def test_dashboard_control_and_centered_collapsed_logo(self):
        self.assertIn('id="sidebarToggle"',HTML)
        self.assertIn('aria-controls="sidebarSessionControls"',HTML)
        self.assertIn('<span>Dashboard</span></button>',HTML)
        self.assertIn('id="brandCollapsedSvg"',HTML)
        self.assertIn('justify-content:center!important',HTML)
        self.assertIn('.sidebarCollapsed .app>aside>.brandRow .brandCollapsedSvg{display:block!important;',HTML)
        self.assertIn('Dashboard: Expand sidebar',HTML)
        self.assertNotIn('>SESSION CONTROLS</div>',HTML)
        self.assertIn('color:var(--connectionColor)',HTML)
        self.assertIn('background:var(--connectionColor)',HTML)
        self.assertIn("'ft-sidebar-collapsed'",HTML)
        self.assertIn('hasCustomLogo .app>aside>.brandRow .brandCollapsedSvg{display:none!important}',HTML)
    def test_series_selector_overlay_center(self):
        self.assertIn('class="previousTargetFrame"',HTML)
        self.assertIn('class="previousControls" role="group"',HTML)
        self.assertIn('previousTargetFrame .previousControls{left:50%!important;',HTML)
        self.assertIn('transform:translateX(-50%)!important',HTML)
        self.assertIn("$('prevSeriesBtn')",HTML)
        self.assertIn("$('nextSeriesBtn')",HTML)

if __name__=='__main__':unittest.main()
