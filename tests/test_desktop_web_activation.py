"""Verify the desktop web update can switch and roll back an isolated site."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def activation(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / 'scripts/vps/activate-node1-desktop-web.py'
    spec = importlib.util.spec_from_file_location('desktop_web_activation', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    site = tmp_path / 'site'
    old = site / 'releases' / module.EXPECTED_CURRENT
    old.mkdir(parents=True)
    (site / 'current').symlink_to(old)
    (old / 'downloads').mkdir()
    (old / 'downloads' / 'existing.apk').write_bytes(b'untouched download')
    stage = tmp_path / 'stage'
    stage.mkdir()
    manifest = {}
    for name in module.REPLACED | module.ADDED:
        source = stage / 'web' / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'new ' + name.encode())
        baseline = None
        if name in module.REPLACED:
            previous = old / name
            previous.parent.mkdir(parents=True, exist_ok=True)
            previous.write_bytes(b'old ' + name.encode())
            baseline = module.digest(previous.read_bytes())
        manifest[name] = {'sha256': module.digest(source.read_bytes()), 'baseSha256': baseline}
    (stage / 'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(module, 'SITE', site)
    monkeypatch.setattr(module, '__file__', str(stage / 'activate.py'))
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    calls = []

    def served(command, timeout):
        calls.append(command)
        assert '--resolve' in command and '--insecure' not in command
        name = command[-1].split('.ru/')[1].split('?')[0]
        if name.endswith('/'):
            name += 'index.html'
        return (site / 'current' / name).read_bytes() + b'\n200'

    monkeypatch.setattr(module.subprocess, 'check_output', served)
    return module, site, old, stage, calls


def test_switch_preserves_downloads_and_verifies_all_changed_urls(activation):
    module, site, old, _, calls = activation
    module.main()
    assert (site / 'current').resolve().name == module.RELEASE
    assert (site / 'current/downloads/existing.apk').read_bytes() == b'untouched download'
    assert (old / 'app/index.html').read_bytes() == b'old app/index.html'
    assert len(calls) == len(module.REPLACED | module.ADDED)
    assert any(call[-1].split('?')[0].endswith('/app/') for call in calls)


def test_changed_production_file_aborts_before_switch(activation):
    module, site, old, _, _ = activation
    (old / 'workspace.js').write_bytes(b'concurrent change')
    with pytest.raises(RuntimeError, match='Production file changed'):
        module.main()
    assert (site / 'current').resolve() == old


def test_wrong_https_response_restores_previous_release(activation, monkeypatch):
    module, site, old, _, _ = activation
    monkeypatch.setattr(module.subprocess, 'check_output', lambda *args, **kwargs: b'wrong\n200')
    with pytest.raises(RuntimeError, match='Served file mismatch'):
        module.main()
    assert (site / 'current').resolve() == old
