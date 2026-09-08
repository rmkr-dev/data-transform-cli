import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  convert,
  detectFormat,
  inferFormat,
  parse,
  serialize,
} from '../src/convert.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixture = (name) => readFileSync(join(__dirname, 'fixtures', name), 'utf8');

describe('detectFormat / inferFormat', () => {
  it('detects by extension', () => {
    assert.equal(detectFormat('a.json'), 'json');
    assert.equal(detectFormat('a.YAML'), 'yaml');
    assert.equal(detectFormat('a.yml'), 'yaml');
    assert.equal(detectFormat('a.csv'), 'csv');
    assert.equal(detectFormat('a.txt'), null);
  });

  it('infers from content', () => {
    assert.equal(inferFormat('{"a":1}'), 'json');
    assert.equal(inferFormat('[1,2]'), 'json');
    assert.equal(inferFormat('a: 1\nb: 2\n'), 'yaml');
    assert.equal(inferFormat('id,name\n1,a\n'), 'csv');
  });
});

describe('convert round-trips', () => {
  it('json → yaml → json preserves data', () => {
    const jsonText = fixture('sample.json');
    const data = parse(jsonText, 'json');
    const yamlText = serialize(data, 'yaml');
    const back = parse(yamlText, 'yaml');
    assert.deepEqual(back, data);
  });

  it('yaml → json → yaml preserves data', () => {
    const yamlText = fixture('sample.yaml');
    const data = parse(yamlText, 'yaml');
    const jsonText = serialize(data, 'json', { pretty: true });
    const back = parse(jsonText, 'json');
    assert.deepEqual(back, data);
  });

  it('json → csv → json preserves stringified fields', () => {
    // CSV is stringly-typed; compare via CSV object shape
    const data = parse(fixture('sample.json'), 'json');
    const asCsvObjects = data.map((row) => ({
      id: String(row.id),
      name: row.name,
      note: row.note,
    }));
    const csv = serialize(asCsvObjects, 'csv');
    const back = parse(csv, 'csv');
    assert.deepEqual(back, asCsvObjects);
  });

  it('csv fixture parses and re-serializes', () => {
    const csvText = fixture('sample.csv');
    const data = parse(csvText, 'csv');
    const again = serialize(data, 'csv');
    assert.deepEqual(parse(again, 'csv'), data);
  });

  it('convert() helper json to yaml', () => {
    const out = convert('{"x":1}', 'json', 'yaml');
    assert.match(out, /x:\s*1/);
  });

  it('pretty and minify json', () => {
    const data = { a: 1, b: [2] };
    const pretty = serialize(data, 'json', { pretty: true });
    const mini = serialize(data, 'json', { minify: true });
    assert.ok(pretty.includes('\n'));
    assert.equal(mini, '{"a":1,"b":[2]}');
    assert.deepEqual(JSON.parse(pretty), data);
    assert.deepEqual(JSON.parse(mini), data);
  });

  it('csv serialize rejects non-arrays', () => {
    assert.throws(() => serialize({ a: 1 }, 'csv'), /array/i);
  });
});
