#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'node:fs';
import { stdin as stdinStream } from 'node:process';
import { Command } from 'commander';
import {
  convert,
  detectFormat,
  inferFormat,
  parse,
  serialize,
} from './convert.js';

const program = new Command();

program
  .name('data-transform')
  .description('YAML ↔ JSON ↔ CSV transforms for pipelines and shell use')
  .version('0.1.0');

/**
 * Read all of stdin as UTF-8 text.
 * @returns {Promise<string>}
 */
function readStdin() {
  return new Promise((resolve, reject) => {
    const chunks = [];
    stdinStream.setEncoding('utf8');
    stdinStream.on('data', (c) => chunks.push(c));
    stdinStream.on('end', () => resolve(chunks.join('')));
    stdinStream.on('error', reject);
  });
}

/**
 * Load input from file path or stdin when path is "-" / omitted.
 * @param {string | undefined} file
 * @returns {Promise<{ text: string, name?: string }>}
 */
async function loadInput(file) {
  if (!file || file === '-') {
    if (stdinStream.isTTY) {
      throw new Error('No input file and stdin is a TTY. Pass a file or pipe data.');
    }
    return { text: await readStdin(), name: undefined };
  }
  return { text: readFileSync(file, 'utf8'), name: file };
}

/**
 * Resolve source format from flag, filename, or content.
 * @param {string} text
 * @param {string | undefined} name
 * @param {string | undefined} fromFlag
 */
function resolveFrom(text, name, fromFlag) {
  if (fromFlag) return fromFlag;
  return detectFormat(name) ?? inferFormat(text);
}

/**
 * Write output to file or stdout.
 * @param {string} out
 * @param {string | undefined} outputPath
 */
function writeOutput(out, outputPath) {
  if (outputPath && outputPath !== '-') {
    writeFileSync(outputPath, out, 'utf8');
  } else {
    process.stdout.write(out);
  }
}

/**
 * Shared options for transform commands.
 * @param {Command} cmd
 */
function addIOOptions(cmd) {
  return cmd
    .argument('[file]', 'input file (default: stdin)')
    .option('-o, --output <file>', 'write to file instead of stdout')
    .option('-f, --from <format>', 'input format: json | yaml | csv');
}

function makeTransformCommand(name, description, toFormat) {
  const cmd = program.command(name).description(description);
  addIOOptions(cmd);
  if (toFormat === 'json') {
    cmd.option('--minify', 'emit compact JSON', false);
  }
  cmd.action(async (file, opts) => {
    try {
      const { text, name } = await loadInput(file);
      const from = resolveFrom(text, name, opts.from);
      const out = convert(text, from, toFormat, {
        pretty: !opts.minify,
        minify: Boolean(opts.minify),
      });
      writeOutput(out, opts.output);
    } catch (err) {
      console.error(`error: ${err.message}`);
      process.exitCode = 1;
    }
  });
}

makeTransformCommand('to-json', 'Convert input to JSON', 'json');
makeTransformCommand('to-yaml', 'Convert input to YAML', 'yaml');
makeTransformCommand('to-csv', 'Convert input to CSV (array of objects/rows)', 'csv');

program
  .command('pretty')
  .description('Pretty-print JSON (or convert to pretty JSON)')
  .argument('[file]', 'input file (default: stdin)')
  .option('-o, --output <file>', 'write to file instead of stdout')
  .option('-f, --from <format>', 'input format: json | yaml | csv')
  .action(async (file, opts) => {
    try {
      const { text, name } = await loadInput(file);
      const from = resolveFrom(text, name, opts.from);
      const data = parse(text, from);
      writeOutput(serialize(data, 'json', { pretty: true }), opts.output);
    } catch (err) {
      console.error(`error: ${err.message}`);
      process.exitCode = 1;
    }
  });

program
  .command('minify')
  .description('Minify JSON (or convert to compact JSON)')
  .argument('[file]', 'input file (default: stdin)')
  .option('-o, --output <file>', 'write to file instead of stdout')
  .option('-f, --from <format>', 'input format: json | yaml | csv')
  .action(async (file, opts) => {
    try {
      const { text, name } = await loadInput(file);
      const from = resolveFrom(text, name, opts.from);
      const data = parse(text, from);
      writeOutput(serialize(data, 'json', { minify: true }), opts.output);
    } catch (err) {
      console.error(`error: ${err.message}`);
      process.exitCode = 1;
    }
  });

program.parseAsync(process.argv);
