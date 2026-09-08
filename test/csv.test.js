import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseCsv, parseCsvRows, stringifyCsv, escapeCsvField } from '../src/csv.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixture = (name) => readFileSync(join(__dirname, 'fixtures', name), 'utf8');

describe('csv', () => {
  it('escapeCsvField quotes special characters', () => {
    assert.equal(escapeCsvField('plain'), 'plain');
    assert.equal(escapeCsvField('a,b'), '"a,b"');
    assert.equal(escapeCsvField('say "hi"'), '"say ""hi"""');
    assert.equal(escapeCsvField('a\nb'), '"a\nb"');
    assert.equal(escapeCsvField(null), '');
  });

  it('parses quoted commas and newlines', () => {
    const rows = parseCsv(fixture('sample.csv'));
    assert.equal(rows.length, 2);
    assert.equal(rows[0].name, 'alpha');
    assert.equal(rows[0].note, 'hello, world');
    assert.equal(rows[1].note, 'line1\nline2');
  });

  it('round-trips object rows', () => {
    const data = [
      { id: '1', name: 'alpha', note: 'hello, world' },
      { id: '2', name: 'beta', note: 'line1\nline2' },
    ];
    const csv = stringifyCsv(data);
    const parsed = parseCsv(csv);
    assert.deepEqual(parsed, data);
  });

  it('parses raw rows without header', () => {
    const rows = parseCsvRows('a,b\n1,2\n');
    assert.deepEqual(rows, [
      ['a', 'b'],
      ['1', '2'],
    ]);
  });

  it('handles empty input', () => {
    assert.deepEqual(parseCsv(''), []);
    assert.equal(stringifyCsv([]), '');
  });
});
