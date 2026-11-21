const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const root = path.resolve(__dirname, '..', '..', '..');
const files = [
  path.resolve(__dirname, '..', 'app', 'assets', 'index.html'),
  path.join(root, 'desktop', 'macos', 'app', 'assets', 'index.html'),
  path.join(root, 'android', 'app', 'src', 'main', 'assets', 'index.html')
].filter(file => fs.existsSync(file));
assert.ok(files.length, 'No application asset found');
for (const file of files) {
  const html = fs.readFileSync(file, 'utf8');
  assert.ok(!html.includes('id="liveHeatmapNote"'), file);
  const start = html.indexOf('function heatmapHits(');
  const end = html.indexOf('function paintHeatmap(', start);
  assert.ok(start >= 0 && end > start, file);
  const context = {
    finiteNumber: value => typeof value === 'number' && Number.isFinite(value),
    heatmapResolution: 50,
    heatmapPeakiness: 3
  };
  vm.createContext(context);
  vm.runInContext(html.slice(start, end), context);
  const targetStart = html.indexOf('function heatmapDescription(');
  const targetEnd = html.indexOf('function initHeatmaps(', targetStart);
  assert.ok(targetStart >= 0 && targetEnd > targetStart, file);
  let drawn = 0;
  let painted = 0;
  context.drawTarget = () => { drawn++; };
  context.paintHeatmap = () => { painted++; return 2; };
  vm.runInContext(html.slice(targetStart, targetEnd), context);
  context.heatmapTarget({}, [], 'pistol');
  const note = {};
  context.heatmapTarget({}, [], 'pistol', note, 'Selected sessions');
  assert.equal(drawn, 2, file);
  assert.equal(painted, 2, file);
  assert.match(note.textContent, /Selected sessions · 2 valid hits/, file);
  const density = context.heatmapDensity;
  const valid = {x: 0, y: 0};
  const invalid = [
    {x: 0, y: 0, miss: true}, {x: 0, y: 0, miss: '1'},
    {x: 0, y: 0, timeout: true}, {x: 0, y: 0, skipped: true},
    {x: 0, y: 0, source: 'stage-advance'}, {x: null, y: 0},
    {x: Infinity, y: 0}
  ];
  assert.equal(density(invalid, 160).hits, 0, file);
  assert.equal(density(invalid, 160).max, 0, file);
  const one = density([valid], 160);
  const two = density([valid, valid, ...invalid], 160);
  assert.equal(two.hits, 2, file);
  const selected = context.selectedSessionHeatmap([
    {item: {shotData: [valid, {x: 2, y: 1, miss: true}]}},
    {item: {shotData: [{x: 20, y: 0}, {x: -10, y: 0}]}},
    {item: {shots: 20}}
  ]);
  assert.equal(selected.summaryOnly, 1, file);
  assert.equal(density(selected.shots, 160).hits, 3, file);
  assert.equal(density(context.selectedSessionHeatmap([]).shots, 160).hits, 0, file);
  assert.ok(Math.abs(two.max - 2 * one.max) < 1e-10, file);
  const shifted = density([{x: 20, y: 0}], 160);
  const peak = values => values.indexOf(Math.max(...values));
  assert.ok(peak(shifted.values) % 50 > peak(one.values) % 50, file);
  const rifle = density([{x: 10, y: 0}], 50);
  assert.ok(peak(rifle.values) % 50 > peak(shifted.values) % 50, file);
  const coarse = density([valid], 160, 25, 3);
  const fine = density([valid], 160, 100, 3);
  assert.equal(coarse.values.length, 625, file);
  assert.equal(fine.values.length, 10000, file);
  const broad = density([valid], 160, 100, 1);
  const sharp = density([valid], 160, 100, 5);
  const offCenter = 49 * 100 + 54;
  assert.ok(sharp.values[offCenter] / sharp.max < broad.values[offCenter] / broad.max, file);
}
console.log(`Heatmap density and hit filtering pass for ${files.length} platform asset(s).`);
