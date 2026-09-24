// Package the reviewed desktop installers and download page for node1.
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const site = resolve(root, 'Web/myherzen.moonbaystudio.ru');
const artifacts = resolve(process.argv[2] || '');
const output = resolve(root, '.local/releases/desktop-downloads-20260924');
const current = '/srv/moonbay/www/myherzen.moonbaystudio.ru/current';
const expected = '/srv/moonbay/www/myherzen.moonbaystudio.ru/releases/20260924-desktop-app-ui-v2';
const sources = {
  'download/index.html': resolve(site, 'download/index.html'),
  'downloads/MyHerzen_1.0.7_x64-setup.exe': resolve(artifacts, 'myherzen-desktop-windows-x86_64/nsis/MyHerzen_1.0.7_x64-setup.exe'),
  'downloads/MyHerzen_1.0.7_amd64.deb': resolve(artifacts, 'myherzen-desktop-linux-x86_64/deb/MyHerzen_1.0.7_amd64.deb'),
  'downloads/MyHerzen_1.0.7_amd64.AppImage': resolve(artifacts, 'myherzen-desktop-linux-x86_64/appimage/MyHerzen_1.0.7_amd64.AppImage'),
};
const installers = Object.keys(sources).filter(name => name.startsWith('downloads/'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

if (!process.argv[2]) throw new Error('Pass the downloaded GitHub Actions artifact directory');
const page = readFileSync(sources['download/index.html'], 'utf8');
for (const name of installers) {
  const basename = name.slice('downloads/'.length);
  const bytes = readFileSync(sources[name]);
  if (!page.includes(name) || !page.includes(hash(bytes))) {
    throw new Error(`Download link or SHA-256 is missing from the page: ${name}`);
  }
}
const remote = execFileSync('ssh', [
  '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'moonbay-node1',
  `cd ${current} && readlink -f . && sha256sum -- download/index.html && for file in ${installers.join(' ')}; do test ! -e "$file" || exit 12; done`
], {encoding: 'utf8'}).trim().split('\n');
if (remote.shift() !== expected) throw new Error('Active web release changed');
const [baseSha256, baseName] = remote[0].trim().split(/\s+/);
if (baseName !== 'download/index.html' || !/^[a-f0-9]{64}$/.test(baseSha256)) {
  throw new Error('Invalid production baseline');
}
if (existsSync(output)) throw new Error(`Package directory already exists: ${output}`);

const manifest = {};
for (const [name, source] of Object.entries(sources)) {
  const destination = resolve(output, 'web', name);
  const data = readFileSync(source);
  mkdirSync(dirname(destination), {recursive: true});
  copyFileSync(source, destination);
  manifest[name] = {sha256: hash(data), bytes: data.length, baseSha256: name === 'download/index.html' ? baseSha256 : null};
}
writeFileSync(resolve(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
copyFileSync(resolve(root, 'scripts/vps/activate-node1-desktop-downloads.py'), resolve(output, 'activate.py'));
const archive = resolve(output, 'update.tar.gz');
execFileSync('tar', ['-czf', archive, '--no-xattrs', '-C', output, 'web', 'manifest.json', 'activate.py'],
  {env: {...process.env, COPYFILE_DISABLE: '1'}});
console.log(archive);
console.log(`SHA256 ${hash(readFileSync(archive))}`);
