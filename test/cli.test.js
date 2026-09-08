import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const cli = join(root, 'src', 'cli.js');
const fixture = (name) => join(__dirname, 'fixtures', name);

/**
 * Run the CLI with args and optional stdin.
 * @param {string[]} args
 * @param {string} [stdinText]
 * @returns {Promise<{ code: number|null, stdout: string, stderr: string }>}
 */
function runCli(args, stdinText) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [cli, ...args], {
      cwd: root,
      env: process.env,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (d) => (stdout += d));
    child.stderr.on('data', (d) => (stderr += d));
    child.on('error', reject);
    child.on('close', (code) => resolve({ code, stdout, stderr }));
    if (stdinText !== undefined) {
      child.stdin.end(stdinText);
    } else {
      child.stdin.end();
    }
  });
}

describe('cli', () => {
  it('to-json from yaml file', async () => {
    const { code, stdout, stderr } = await runCli(['to-json', fixture('sample.yaml')]);
    assert.equal(code, 0, stderr);
    const data = JSON.parse(stdout);
    assert.equal(data[0].name, 'alpha');
  });

  it('to-yaml from json file', async () => {
    const { code, stdout, stderr } = await runCli(['to-yaml', fixture('sample.json')]);
    assert.equal(code, 0, stderr);
    assert.match(stdout, /name:\s*alpha/);
  });

  it('to-csv from json via stdin', async () => {
    const input = readFileSync(fixture('sample.json'), 'utf8');
    const { code, stdout, stderr } = await runCli(['to-csv', '-f', 'json'], input);
    assert.equal(code, 0, stderr);
    assert.match(stdout, /^id,name,note/m);
    assert.match(stdout, /hello, world/);
  });

  it('pretty formats compact json from stdin', async () => {
    const { code, stdout, stderr } = await runCli(['pretty', '-f', 'json'], '{"a":1}');
    assert.equal(code, 0, stderr);
    assert.equal(stdout, '{\n  "a": 1\n}\n');
  });

  it('minify collapses json', async () => {
    const { code, stdout, stderr } = await runCli(
      ['minify', '-f', 'json'],
      '{\n  "a": 1\n}\n'
    );
    assert.equal(code, 0, stderr);
    assert.equal(stdout, '{"a":1}');
  });

  it('to-json --minify emits compact output', async () => {
    const { code, stdout, stderr } = await runCli([
      'to-json',
      '--minify',
      fixture('sample.yaml'),
    ]);
    assert.equal(code, 0, stderr);
    assert.ok(!stdout.includes('\n  '));
    assert.ok(JSON.parse(stdout));
  });
});
