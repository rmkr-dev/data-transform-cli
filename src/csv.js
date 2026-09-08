/**
 * Simple, robust CSV parse/stringify (RFC 4180-ish).
 * Supports quoted fields, escaped quotes, and newlines inside quotes.
 */

/**
 * Parse a CSV string into an array of row objects (header row required)
 * or an array of arrays if noHeader is true.
 * @param {string} text
 * @param {{ noHeader?: boolean }} [opts]
 * @returns {object[] | string[][]}
 */
export function parseCsv(text, opts = {}) {
  const rows = parseCsvRows(text);
  if (rows.length === 0) return [];

  if (opts.noHeader) return rows;

  const headers = rows[0].map((h) => h.trim());
  return rows.slice(1).map((cells) => {
    const obj = {};
    for (let i = 0; i < headers.length; i++) {
      obj[headers[i]] = cells[i] ?? '';
    }
    return obj;
  });
}

/**
 * Parse CSV into raw rows (arrays of strings).
 * @param {string} text
 * @returns {string[][]}
 */
export function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let field = '';
  let i = 0;
  let inQuotes = false;
  const s = String(text).replace(/^\uFEFF/, '');

  while (i < s.length) {
    const c = s[i];

    if (inQuotes) {
      if (c === '"') {
        if (s[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i += 1;
        continue;
      }
      field += c;
      i += 1;
      continue;
    }

    if (c === '"') {
      inQuotes = true;
      i += 1;
      continue;
    }

    if (c === ',') {
      row.push(field);
      field = '';
      i += 1;
      continue;
    }

    if (c === '\r') {
      i += 1;
      continue;
    }

    if (c === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
      i += 1;
      continue;
    }

    field += c;
    i += 1;
  }

  // trailing field / row (including empty trailing newline handled above)
  if (field.length > 0 || row.length > 0 || (s.length > 0 && !s.endsWith('\n') && !s.endsWith('\r'))) {
    row.push(field);
    rows.push(row);
  } else if (row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  // Drop a single trailing empty row produced by a final newline
  if (rows.length > 0) {
    const last = rows[rows.length - 1];
    if (last.length === 1 && last[0] === '' && text.match(/\r?\n$/)) {
      rows.pop();
    }
  }

  return rows;
}

/**
 * Escape a single CSV field.
 * @param {unknown} value
 * @returns {string}
 */
export function escapeCsvField(value) {
  if (value === null || value === undefined) return '';
  const str = typeof value === 'object' ? JSON.stringify(value) : String(value);
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/**
 * Stringify data to CSV.
 * Accepts array of objects (uses union of keys as header) or array of arrays.
 * @param {object[] | unknown[][]} data
 * @param {{ headers?: string[] }} [opts]
 * @returns {string}
 */
export function stringifyCsv(data, opts = {}) {
  if (!Array.isArray(data) || data.length === 0) {
    if (opts.headers?.length) {
      return opts.headers.map(escapeCsvField).join(',') + '\n';
    }
    return '';
  }

  const first = data[0];
  const isObjects = first !== null && typeof first === 'object' && !Array.isArray(first);

  if (isObjects) {
    const headers =
      opts.headers ??
      Array.from(
        data.reduce((set, row) => {
          Object.keys(row ?? {}).forEach((k) => set.add(k));
          return set;
        }, new Set())
      );
    const lines = [headers.map(escapeCsvField).join(',')];
    for (const row of data) {
      lines.push(headers.map((h) => escapeCsvField(row?.[h])).join(','));
    }
    return lines.join('\n') + '\n';
  }

  // array of arrays
  const lines = data.map((row) =>
    (Array.isArray(row) ? row : [row]).map(escapeCsvField).join(',')
  );
  return lines.join('\n') + '\n';
}
