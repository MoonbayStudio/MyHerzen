#!/usr/bin/env python3
"""Switch only the MyHerzen static site to the reviewed desktop /app UI."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

SITE = Path('/srv/moonbay/www/myherzen.moonbaystudio.ru')
EXPECTED_CURRENT = '20260918-downloads-1.0-7'
RELEASE = '20260924-desktop-app-ui-v2'
REPLACED = {
    'app/index.html', 'workspace.css', 'workspace.js', 'styles.css',
    'nav.js', 'app-sw.js',
}
ADDED = {
    'app/manifest.json', 'img/icon-192.png', 'img/icon-512.png',
    'img/icon-maskable-512.png',
}


def read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 2 * 1024 * 1024:
            raise RuntimeError(f'Not a small regular file: {path}')
        return stream.read()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def switch_to(release):
    temporary = SITE / ('.current-' + RELEASE)
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeError('Activation link already exists')
    temporary.symlink_to('releases/' + release.name)
    temporary.replace(SITE / 'current')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run from the root console on moonbay-node1.')
    stage = Path(__file__).resolve().parent
    manifest = json.loads(read_regular(stage / 'manifest.json'))
    if set(manifest) != REPLACED | ADDED:
        raise RuntimeError('Unexpected file list')
    current = (SITE / 'current').resolve(strict=True)
    if current.parent != SITE / 'releases' or current.name != EXPECTED_CURRENT:
        raise RuntimeError('Active release changed; rebase the update first')
    for path in current.rglob('*'):
        if path.is_symlink():
            raise RuntimeError(f'Unexpected symlink in static release: {path}')

    payload = {}
    for name, hashes in manifest.items():
        source = stage / 'web' / name
        if any(parent.is_symlink() for parent in source.parents):
            raise RuntimeError('Symlink in staged path')
        data = read_regular(source)
        if digest(data) != hashes['sha256']:
            raise RuntimeError(f'Payload checksum mismatch: {name}')
        target = current / name
        if name in REPLACED:
            if digest(read_regular(target)) != hashes['baseSha256']:
                raise RuntimeError(f'Production file changed: {name}')
        elif target.exists() or target.is_symlink() or hashes['baseSha256'] is not None:
            raise RuntimeError(f'New path already exists: {name}')
        payload[name] = data

    release = SITE / 'releases' / RELEASE
    shutil.copytree(current, release)  # Preserve the old release, downloads and all untouched files.
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
            public_path = name[:-len('index.html')] if name.endswith('index.html') else name
            result = subprocess.check_output([
                'curl', '--fail', '--silent', '--show-error', '--max-time', '15',
                '--resolve', 'myherzen.moonbaystudio.ru:443:127.0.0.1',
                '--write-out', '\n%{http_code}',
                'https://myherzen.moonbaystudio.ru/' + public_path + '?release=' + RELEASE,
            ], timeout=20)
            body, separator, status = result.rpartition(b'\n')
            if not separator or status != b'200':
                code = status.decode('ascii', errors='replace')[:80]
                raise RuntimeError(f'Expected HTTP 200 for {public_path}, got {code}')
            if digest(body) != manifest[name]['sha256']:
                raise RuntimeError(f'Served file mismatch: {name}')
    except Exception:
        switch_to(current)
        print('Validation failed. Previous web release restored:', current)
        raise
    print('Activated MyHerzen desktop web UI; ten HTTPS content checks passed.')
    print('Rollback release retained:', current)
    print('No API, database, nginx configuration, downloads or other Moonbay app was changed.')


if __name__ == '__main__':
    main()
