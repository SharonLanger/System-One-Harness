const fs = require('node:fs');
const path = require('node:path');

const projectRoot = path.resolve(__dirname, '../..');
const output = path.join(projectRoot, 'build/typescript');
const dependencies = path.join(projectRoot, 'typescript-helper/node_modules');
const link = path.join(output, 'node_modules');
if (!fs.statSync(dependencies, {throwIfNoEntry: false})?.isDirectory()) {
  throw new Error('Install helper dependencies first: npm --prefix typescript-helper ci');
}
fs.mkdirSync(output, {recursive: true});
const target = process.platform === 'win32' ? dependencies : path.relative(output, dependencies);
const current = fs.lstatSync(link, {throwIfNoEntry: false});
if (current) {
  if (!current.isSymbolicLink() || path.resolve(output, fs.readlinkSync(link)) !== dependencies) {
    throw new Error('Unexpected build/typescript/node_modules; inspect it before rebuilding');
  }
} else {
  fs.symlinkSync(target, link, process.platform === 'win32' ? 'junction' : 'dir');
}
