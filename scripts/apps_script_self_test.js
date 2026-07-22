'use strict';

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const serverFiles = ['apps-script/Code.gs', 'apps-script/Domain.gs', 'apps-script/Tests.gs'];
const context = vm.createContext({ console });

for (const relativePath of serverFiles) {
  const source = fs.readFileSync(path.join(root, relativePath), 'utf8');
  new vm.Script(source, { filename: relativePath }).runInContext(context);
}

const result = new vm.Script('runAllTests()', { filename: 'runAllTests' }).runInContext(context);
if (!result || result.ok !== true || result.passed !== 5) {
  throw new Error(`Apps Script self-tests failed: ${JSON.stringify(result)}`);
}

const clientPath = path.join(root, 'apps-script/Scripts.html');
const clientSource = fs
  .readFileSync(clientPath, 'utf8')
  .replace(/^\s*<script>\s*/, '')
  .replace(/\s*<\/script>\s*$/, '');
new vm.Script(clientSource, { filename: 'apps-script/Scripts.html' });

console.log(`Apps Script checks passed: ${result.passed} server tests + client JavaScript syntax.`);
