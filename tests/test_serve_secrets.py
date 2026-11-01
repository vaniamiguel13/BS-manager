import os
from pathlib import Path
import runpy
import shutil
import stat

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "serve.py"


def run_copied_serve(tmp_path, monkeypatch):
    script = tmp_path / "serve.py"
    shutil.copyfile(SOURCE, script)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("BS_MANAGER_SERVE_TEST_SETTING", raising=False)
    runpy.run_path(str(script))
    return tmp_path / ".env"


@pytest.mark.skipif(os.name == "nt", reason="POSIX file permission bits are not available on Windows")
def test_fresh_generated_env_is_created_private(tmp_path, monkeypatch):
    env_file = run_copied_serve(tmp_path, monkeypatch)

    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    lines = env_file.read_text(encoding="utf-8").splitlines()
    keys = [line.partition("=")[2] for line in lines if line.startswith("SECRET_KEY=")]
    assert len(keys) == 1 and len(keys[0]) == 64


def test_existing_env_permissions_are_hardened_and_settings_preserved(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    original = "BS_MANAGER_SERVE_TEST_SETTING=preserved-value\n# Keep this comment\n"
    env_file.write_text(original, encoding="utf-8")
    if os.name != "nt":
        env_file.chmod(0o644)

    result = run_copied_serve(tmp_path, monkeypatch)
    contents = result.read_text(encoding="utf-8")

    assert "BS_MANAGER_SERVE_TEST_SETTING=preserved-value" in contents
    assert "# Keep this comment" in contents
    assert contents.count("SECRET_KEY=") == 1
    if os.name != "nt":
        assert stat.S_IMODE(result.stat().st_mode) == 0o600


def test_env_symlink_is_rejected_without_modifying_target(tmp_path, monkeypatch):
    target = tmp_path / "outside.env"
    original = "BS_MANAGER_SERVE_TEST_SETTING=external-value\n"
    target.write_text(original, encoding="utf-8")
    env_link = tmp_path / ".env"
    try:
        env_link.symlink_to(target)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Symlink creation is unavailable: {type(error).__name__}")

    script = tmp_path / "serve.py"
    shutil.copyfile(SOURCE, script)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("BS_MANAGER_SERVE_TEST_SETTING", raising=False)

    with pytest.raises(RuntimeError, match="symlinked .env"):
        runpy.run_path(str(script))

    assert env_link.is_symlink()
    assert target.read_text(encoding="utf-8") == original
