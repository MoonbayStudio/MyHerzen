// Package only the reviewed /app redesign and its public assets.
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const site = resolve(root, 'Web/myherzen.moonbaystudio.ru');
const output = resolve(root, '.local/releases/desktop-web-20260924-v2');
const current = '/srv/moonbay/www/myherzen.moonbaystudio.ru/current';
const expected = '/srv/moonbay/www/myherzen.moonbaystudio.ru/releases/20260918-downloads-1.0-7';
const replaced = ['app/index.html', 'workspace.css', 'workspace.js', 'styles.css', 'nav.js', 'app-sw.js'];
const added = ['app/manifest.json', 'img/icon-192.png', 'img/icon-512.png', 'img/icon-maskable-512.png'];
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

const appHtml = readFileSync(resolve(site, 'app/index.html'), 'utf8');
for (const name of ['styles.css', 'workspace.css', 'auth.js', 'nav.js', 'client-core.js', 'workspace.js']) {
  if (!appHtml.includes(`${name}?v=20260924-desktop`)) {
    throw new Error(`Missing current asset version in app/index.html: ${name}`);
  }
}

const remote = execFileSync('ssh', [
  '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'moonbay-node1',
  `cd ${current} && readlink -f . && sha256sum -- ${replaced.join(' ')} && for file in ${added.join(' ')}; do test ! -e "$file" || exit 12; done`
], {encoding: 'utf8'}).trim().split('\n');
if (remote.shift() !== expected) throw new Error('The active web release changed');
const baseline = Object.fromEntries(remote.map(line => {
  const [digest, name] = line.trim().split(/\s+/);
  if (!/^[a-f0-9]{64}$/.test(digest)) throw new Error('Invalid remote checksum');
  return [name, digest];
}));
if (replaced.some(name => !baseline[name])) throw new Error('Missing production baseline');
if (existsSync(output)) throw new Error(`Package directory already exists: ${output}`);

const manifest = {};
for (const name of [...replaced, ...added]) {
  const source = resolve(site, name);
  const destination = resolve(output, 'web', name);
  const data = readFileSync(source);
  mkdirSync(dirname(destination), {recursive: true});
  copyFileSync(source, destination);
  manifest[name] = {sha256: hash(data), baseSha256: baseline[name] || null};
}
writeFileSync(resolve(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
copyFileSync(resolve(root, 'scripts/vps/activate-node1-desktop-web.py'), resolve(output, 'activate.py'));
const archive = resolve(output, 'update.tar.gz');
execFileSync('tar', ['-czf', archive, '--no-xattrs', '-C', output, 'web', 'manifest.json', 'activate.py'],
  {env: {...process.env, COPYFILE_DISABLE: '1'}});
console.log(archive);
console.log(`SHA256 ${hash(readFileSync(archive))}`);
