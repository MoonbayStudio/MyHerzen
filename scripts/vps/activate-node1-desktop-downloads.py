#!/usr/bin/env python3
"""Atomically publish the pinned desktop installers and download page."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

SITE = Path('/srv/moonbay/www/myherzen.moonbaystudio.ru')
EXPECTED_CURRENT = '20260924-desktop-app-ui-v2'
RELEASE = '20260924-desktop-downloads-1.0.7'
REPLACED = {'download/index.html'}
ADDED = {
    'downloads/MyHerzen_1.0.7_x64-setup.exe',
    'downloads/MyHerzen_1.0.7_amd64.deb',
    'downloads/MyHerzen_1.0.7_amd64.AppImage',
}
LIMITS = {'download/index.html': 1_000_000,
          'downloads/MyHerzen_1.0.7_x64-setup.exe': 10_000_000,
          'downloads/MyHerzen_1.0.7_amd64.deb': 10_000_000,
          'downloads/MyHerzen_1.0.7_amd64.AppImage': 100_000_000}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise RuntimeError(f'Invalid regular file: {path}')
        return stream.read()


def switch_to(release):
    temporary = SITE / ('.current-' + RELEASE)
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeError('Activation link already exists')
    temporary.symlink_to('releases/' + release.name)
    temporary.replace(SITE / 'current')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root on moonbay-node1.')
    stage = Path(__file__).resolve().parent
    manifest = json.loads(read_regular(stage / 'manifest.json', 100_000))
    if set(manifest) != REPLACED | ADDED:
        raise RuntimeError('Unexpected payload paths')
    current = (SITE / 'current').resolve(strict=True)
    if current.parent != SITE / 'releases' or current.name != EXPECTED_CURRENT:
        raise RuntimeError('Active release changed')
    for path in current.rglob('*'):
        if path.is_symlink():
            raise RuntimeError(f'Unexpected symlink: {path}')

    payload = {}
    for name, metadata in manifest.items():
        source = stage / 'web' / name
        if any(parent.is_symlink() for parent in source.parents):
            raise RuntimeError('Symlink in staged path')
        data = read_regular(source, LIMITS[name])
        if len(data) != metadata['bytes'] or digest(data) != metadata['sha256']:
            raise RuntimeError(f'Payload mismatch: {name}')
        target = current / name
        if name in REPLACED:
            if digest(read_regular(target, LIMITS[name])) != metadata['baseSha256']:
                raise RuntimeError(f'Production file changed: {name}')
        elif target.exists() or target.is_symlink() or metadata['baseSha256'] is not None:
            raise RuntimeError(f'New path already exists: {name}')
        payload[name] = data

    release = SITE / 'releases' / RELEASE
    shutil.copytree(current, release)
    for name, data in payload.items():
        target = release / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o644)
    for directory in [release] + [p for p in release.rglob('*') if p.is_dir()]:
        directory.chmod(0o755)

    switch_to(release)
    try:
        for name in sorted(REPLACED | ADDED):
            with tempfile.NamedTemporaryFile() as response:
                result = subprocess.check_output([
                    'curl', '--fail', '--silent', '--show-error', '--max-time', '90',
                    '--resolve', 'myherzen.moonbaystudio.ru:443:127.0.0.1',
                    '--output', response.name, '--write-out', '%{http_code}',
                    'https://myherzen.moonbaystudio.ru/' +
                    ('download/' if name == 'download/index.html' else name) + '?release=' + RELEASE,
                ], timeout=95)
                if result != b'200' or digest(Path(response.name).read_bytes()) != manifest[name]['sha256']:
                    raise RuntimeError(f'HTTPS content mismatch: {name}')
    except Exception:
        switch_to(current)
        print('Validation failed. Previous release restored:', current)
        raise
    print('Activated MyHerzen desktop downloads; four HTTPS content checks passed.')
    print('Rollback release retained:', current)


if __name__ == '__main__':
    main()
