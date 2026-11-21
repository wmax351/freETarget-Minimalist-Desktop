"""Optional developer regressions. Requires Node 18+; no npm packages."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from storage import validate_storage


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = {'tag': 'document', 'attrs': {}, 'children': []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'children': []}
        self.stack[-1]['children'].append(node)
        if tag not in ['input', 'meta', 'link', 'br', 'hr', 'img', 'source']:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]['tag'] == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1]['children'].append(data)


def main():
    node = shutil.which('node')
    if not node:
        raise SystemExit('Install Node 18+ to run these developer tests. The app does not require Node.')
    html = (ROOT / 'app/assets/index.html').read_text(encoding='utf-8')
    parser = Parser()
    parser.feed(html)
    script = re.search(r'<script>([\s\S]*?)</script>', html).group(1)
    cues = re.search(r'const FIVE_CUES=(\{.*?\});', script).group(1)
    with tempfile.TemporaryDirectory(prefix='freetarget-ui-tests-') as folder:
        fixtures = Path(folder)
        (fixtures / 'dom179.json').write_text(json.dumps(parser.root), encoding='utf-8')
        (fixtures / 'check179.js').write_text(script, encoding='utf-8')
        (fixtures / 'cue-data179.js').write_text('const FIVE_CUES=' + cues + ';', encoding='utf-8')
        env = {**os.environ, 'FT_TEST_FIXTURES': folder}
        for name in ('test_ui.cjs', 'test_five.cjs', 'test_stats.cjs', 'test_heatmap.cjs', 'test_bootstrap.cjs', 'test_exporter.cjs'):
            subprocess.run([node, str(ROOT / 'tests' / name)], env=env, cwd=ROOT, check=True)
        values = json.loads((fixtures / 'storage179.json').read_text(encoding='utf-8'))
        validate_storage(values)
        print('Desktop storage validator accepts real UI-generated profiles, history, rules and preferences.')


if __name__ == '__main__':
    main()
