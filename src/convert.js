import yaml from 'js-yaml';
import { parseCsv, stringifyCsv } from './csv.js';

/**
 * Detect format from filename extension.
 * @param {string} [filename]
 * @returns {'json' | 'yaml' | 'csv' | null}
 */
export function detectFormat(filename) {
  if (!filename) return null;
  const lower = filename.toLowerCase();
  if (lower.endsWith('.json')) return 'json';
  if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return 'yaml';
  if (lower.endsWith('.csv')) return 'csv';
  return null;
}

/**
 * Parse input text as the given format.
 * @param {string} text
 * @param {'json' | 'yaml' | 'csv'} format
 * @returns {unknown}
 */
export function parse(text, format) {
  switch (format) {
    case 'json':
      return JSON.parse(text);
    case 'yaml':
      return yaml.load(text);
    case 'csv':
      return parseCsv(text);
    default:
      throw new Error(`Unsupported parse format: ${format}`);
  }
}

/**
 * Serialize data to the given format.
 * @param {unknown} data
 * @param {'json' | 'yaml' | 'csv'} format
 * @param {{ pretty?: boolean, minify?: boolean }} [opts]
 * @returns {string}
 */
export function serialize(data, format, opts = {}) {
  switch (format) {
    case 'json': {
      if (opts.minify) return JSON.stringify(data);
      const space = opts.pretty === false ? 0 : 2;
      return JSON.stringify(data, null, space) + (space ? '\n' : '');
    }
    case 'yaml':
      return yaml.dump(data, { lineWidth: -1, noRefs: true });
    case 'csv': {
      if (!Array.isArray(data)) {
        throw new Error('CSV output requires an array (of objects or rows)');
      }
      return stringifyCsv(data);
    }
    default:
      throw new Error(`Unsupported serialize format: ${format}`);
  }
}

/**
 * Convert between formats.
 * @param {string} text
 * @param {'json' | 'yaml' | 'csv'} from
 * @param {'json' | 'yaml' | 'csv'} to
 * @param {{ pretty?: boolean, minify?: boolean }} [opts]
 * @returns {string}
 */
export function convert(text, from, to, opts = {}) {
  const data = parse(text, from);
  return serialize(data, to, opts);
}

/**
 * Infer source format from content heuristics when extension is unknown.
 * @param {string} text
 * @returns {'json' | 'yaml' | 'csv'}
 */
export function inferFormat(text) {
  const trimmed = text.trimStart();
  if (!trimmed) return 'json';
  if (trimmed[0] === '{' || trimmed[0] === '[') {
    try {
      JSON.parse(text);
      return 'json';
    } catch {
      // fall through
    }
  }
  const firstLine = trimmed.split(/\r?\n/, 1)[0] ?? '';
  if (firstLine.includes(',') && !trimmed.startsWith('---') && !/:\s/.test(firstLine)) {
    return 'csv';
  }
  return 'yaml';
}
