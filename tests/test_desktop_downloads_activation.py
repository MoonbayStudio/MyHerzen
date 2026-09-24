"""Check the desktop installer release switch and HTTPS rollback."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def activation(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / 'scripts/vps/activate-node1-desktop-downloads.py'
    spec = importlib.util.spec_from_file_location('desktop_downloads_activation', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    site = tmp_path / 'site'
    old = site / 'releases' / module.EXPECTED_CURRENT
    old.mkdir(parents=True)
    (site / 'current').symlink_to(old)
    (old / 'downloads').mkdir()
    (old / 'downloads' / 'existing.apk').write_bytes(b'untouched download')
    (old / 'download').mkdir()
    (old / 'download/index.html').write_bytes(b'old page')
    stage = tmp_path / 'stage'
    stage.mkdir()
    manifest = {}
    for name in module.REPLACED | module.ADDED:
        source = stage / 'web' / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'new ' + name.encode())
        manifest[name] = {
            'sha256': module.digest(source.read_bytes()),
            'bytes': source.stat().st_size,
            'baseSha256': module.digest(b'old page') if name in module.REPLACED else None,
        }
    (stage / 'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(module, 'SITE', site)
    monkeypatch.setattr(module, '__file__', str(stage / 'activate.py'))
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    calls = []

    def served(command, timeout):
        calls.append(command)
        assert '--resolve' in command and '--insecure' not in command
        name = command[-1].split('.ru/')[1].split('?')[0]
        if name == 'download/':
            name += 'index.html'
        Path(command[command.index('--output') + 1]).write_bytes((site / 'current' / name).read_bytes())
        return b'200'

    monkeypatch.setattr(module.subprocess, 'check_output', served)
    return module, site, old, calls


def test_switch_preserves_old_downloads_and_verifies_new_files(activation):
    module, site, old, calls = activation
    module.main()
    assert (site / 'current').resolve().name == module.RELEASE
    assert (site / 'current/downloads/existing.apk').read_bytes() == b'untouched download'
    assert (old / 'download/index.html').read_bytes() == b'old page'
    assert len(calls) == 4


def test_changed_page_aborts_before_switch(activation):
    module, site, old, _ = activation
    (old / 'download/index.html').write_bytes(b'changed page')
    with pytest.raises(RuntimeError, match='Production file changed'):
        module.main()
    assert (site / 'current').resolve() == old


def test_bad_https_response_restores_previous_release(activation, monkeypatch):
    module, site, old, _ = activation
    monkeypatch.setattr(module.subprocess, 'check_output', lambda *args, **kwargs: b'500')
    with pytest.raises(RuntimeError, match='HTTPS content mismatch'):
        module.main()
    assert (site / 'current').resolve() == old
