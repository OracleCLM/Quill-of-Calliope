"""Tests for scan_scene_yaml_errors.py — monkeypatch sys.argv for coverage instrumentation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
import scan_scene_yaml_errors as sye  # noqa: E402


def _run_main(monkeypatch, scenes_dir, output_file):
    monkeypatch.setattr(sys, "argv", [
        "scan_scene_yaml_errors.py",
        "--scenes-dir", str(scenes_dir),
        "--output", str(output_file),
    ])
    sye.main()


def test_no_errors(tmp_path, monkeypatch):
    sd = tmp_path / "s"; sd.mkdir()
    (sd / "a.yaml").write_text("k: v\n")
    (sd / "b.yaml").write_text("x: 1\n")
    out = tmp_path / "out.md"
    _run_main(monkeypatch, sd, out)
    assert "0" in out.read_text()


def test_finds_syntax_error(tmp_path, monkeypatch):
    sd = tmp_path / "s"; sd.mkdir()
    (sd / "bad.yaml").write_text("key: {invalid\n")
    out = tmp_path / "out.md"
    _run_main(monkeypatch, sd, out)
    assert "bad.yaml" in out.read_text()


def test_empty_dir(tmp_path, monkeypatch):
    sd = tmp_path / "s"; sd.mkdir()
    out = tmp_path / "out.md"
    _run_main(monkeypatch, sd, out)
    assert out.exists()


def test_real_scenes_dir(tmp_path, monkeypatch):
    scenes = Path(__file__).parents[2] / "scenes"
    out = tmp_path / "out.md"
    _run_main(monkeypatch, scenes, out)
    assert out.stat().st_size > 0


def test_error_table_format(tmp_path, monkeypatch):
    sd = tmp_path / "s"; sd.mkdir()
    (sd / "bad.yaml").write_text("key: {invalid\n")
    out = tmp_path / "out.md"
    _run_main(monkeypatch, sd, out)
    assert "|" in out.read_text()


def test_valid_and_invalid_mixed(tmp_path, monkeypatch):
    sd = tmp_path / "s"; sd.mkdir()
    (sd / "good.yaml").write_text("scene_id: s1\nsummary: ok\n")
    (sd / "bad.yaml").write_text("key: {broken\n")
    out = tmp_path / "out.md"
    _run_main(monkeypatch, sd, out)
    content = out.read_text()
    assert "bad.yaml" in content
    assert "1" in content  # 1 error
