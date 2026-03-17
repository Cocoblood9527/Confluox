from pathlib import Path

from gateway import resource_resolver


def test_get_resource_path_in_dev_env(monkeypatch) -> None:
    monkeypatch.delattr(resource_resolver.sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(resource_resolver.sys, "frozen", False, raising=False)

    expected_base = Path(resource_resolver.__file__).resolve().parent.parent
    path = resource_resolver.get_resource_path("foo/bar.txt")

    assert path == str(expected_base / "foo/bar.txt")


def test_get_resource_path_in_pyinstaller_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(resource_resolver.sys, "_MEIPASS", str(tmp_path), raising=False)

    path = resource_resolver.get_resource_path("foo/bar.txt")

    assert path == str(tmp_path / "foo/bar.txt")


def test_get_resource_path_in_frozen_env(monkeypatch, tmp_path) -> None:
    monkeypatch.delattr(resource_resolver.sys, "_MEIPASS", raising=False)
    fake_executable = tmp_path / "bin" / "gateway"
    fake_executable.parent.mkdir(parents=True, exist_ok=True)
    fake_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(resource_resolver.sys, "frozen", True, raising=False)
    monkeypatch.setattr(resource_resolver.sys, "executable", str(fake_executable), raising=False)

    path = resource_resolver.get_resource_path("foo/bar.txt")

    assert path == str(fake_executable.parent.resolve() / "foo/bar.txt")
