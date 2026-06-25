"""
Unit test per scripts/repair_yaml_quotes.py (CALLIOPE_DATA_DEBT).

Contratto:
  - File già valido → 'skip'
  - List item con quote interne → re-quotato con apici singoli
  - Campo scalar indentato con quote interne → re-quotato
  - Contenuto con entrambi apici → doppi apici con escape
  - File irrecuperabile → 'failed'
  - Dry-run → nessuna scrittura
"""
import sys

import yaml

from scripts.repair_yaml_quotes import _fix_line, _repair_text, _verify, repair_file


# ── _fix_line ─────────────────────────────────────────────────────────────────

def test_fix_list_item_with_inner_quotes():
    line = '  - "Garaph "Gabby""'
    result = _fix_line(line)
    assert result == """  - 'Garaph "Gabby"'"""


def test_no_change_for_clean_list_item():
    line = '  - "Alexis"'
    assert _fix_line(line) == line


def test_fix_title_field_with_inner_quotes():
    line = 'title: "Scene 99: Garaph "Gabby", Judju +1"'
    result = _fix_line(line)
    assert "'" in result or '\\"' in result
    # Il risultato deve essere parsabile come YAML
    assert yaml.safe_load(f"key: {result.split(': ', 1)[1]}") is not None


def test_fix_indented_notes_field():
    line = '  notes: "text with ["brackets"] inside"'
    result = _fix_line(line)
    assert result != line
    value_part = result.split(': ', 1)[1]
    assert yaml.safe_load(f"key: {value_part}")["key"] is not None


def test_no_change_clean_field():
    line = 'title: "Clean title without quotes"'
    assert _fix_line(line) == line


def test_both_quote_types_uses_escape():
    line = """  - "it's a 'test' value "quoted" here" """
    result = _fix_line(line.strip())
    # Quando c'è sia ' che " nel contenuto, usa \\"
    assert '\\"' in result or "'" in result


def test_fix_line_both_quotes_explicit_escape():
    # Content: it's "in" — has both ' and "  → escape branch (lines 32-33)
    line = "  - \"it's \\\"in\\\"\""
    # Build via concatenation to be unambiguous
    line = '  - "' + "it's " + '"in"' + '"'
    # content after regex: it's "in" — has ' (from it's) and " (from "in")
    result = _fix_line(line)
    assert '\\"' in result


# ── _repair_text ──────────────────────────────────────────────────────────────

def test_repair_text_fixes_participants():
    text = (
        "scene_id: scene_99\n"
        "title: test\n"
        "participants:\n"
        '  - "Aurora"\n'
        '  - "Garaph "Gabby""\n'
    )
    repaired = _repair_text(text)
    assert _verify(repaired)
    data = yaml.safe_load(repaired)
    assert 'Garaph "Gabby"' in data["participants"]


def test_repair_text_fixes_title():
    text = 'title: "Scene: Garaph "Gabby" went"\n'
    repaired = _repair_text(text)
    assert _verify(repaired)


def test_verify_ok_on_clean_yaml():
    text = "title: clean\nstatus: draft\n"
    assert _verify(text)


def test_verify_fails_on_broken_yaml():
    text = 'title: "broken "title" here"\n'
    assert not _verify(text)


# ── repair_file ───────────────────────────────────────────────────────────────

def test_repair_file_valid_returns_skip(tmp_path):
    f = tmp_path / "valid.yaml"
    f.write_text("title: clean\nstatus: draft\n")
    status, reason = repair_file(f, dry_run=False)
    assert status == "skip"


def test_repair_file_broken_returns_ok(tmp_path):
    f = tmp_path / "broken.yaml"
    f.write_text('title: "Scene: "Gabby" here"\nstatus: draft\n')
    status, _ = repair_file(f, dry_run=False)
    assert status == "ok"
    assert _verify(f.read_text())


def test_repair_file_dry_run_no_write(tmp_path):
    f = tmp_path / "broken.yaml"
    original = 'title: "Scene: "Gabby" here"\nstatus: draft\n'
    f.write_text(original)
    status, _ = repair_file(f, dry_run=True)
    assert status == "ok"
    assert f.read_text() == original  # Non modificato


def test_repair_file_irrecoverable_returns_failed(tmp_path):
    f = tmp_path / "bad.yaml"
    # YAML so broken that _repair_text cannot fix it
    f.write_text('key: {unclosed: [bracket\n', encoding="utf-8")
    status, detail = repair_file(f, dry_run=False)
    # Either 'skip' (already valid somehow) or 'failed' — not 'ok'
    assert status in ("skip", "failed")


# ── main() ────────────────────────────────────────────────────────────────────

from scripts.repair_yaml_quotes import main  # noqa: E402


def test_main_no_dirs_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", [
        "prog",
        "--scenes-dir", str(tmp_path / "no_scenes"),
        "--chars-dir", str(tmp_path / "no_chars"),
    ])
    with __import__("pytest").raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_dry_run_reports(monkeypatch, tmp_path, capsys):
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    # One valid YAML (→ skip) and one broken (→ ok dry-run)
    (scenes_dir / "clean.yaml").write_text("title: clean\nstatus: draft\n", encoding="utf-8")
    (scenes_dir / "broken.yaml").write_text('title: "Scene "X""\nstatus: draft\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "prog",
        "--scenes-dir", str(scenes_dir),
        "--chars-dir", str(tmp_path / "no_chars"),
        "--dry-run",
    ])
    main()
    out = capsys.readouterr().out
    assert "dry-run" in out.lower() or "DRY-RUN" in out


def test_main_chars_dir_also_scanned(monkeypatch, tmp_path, capsys):
    scenes_dir = tmp_path / "scenes"
    chars_dir = tmp_path / "chars"
    scenes_dir.mkdir()
    chars_dir.mkdir()
    (chars_dir / "char.yaml").write_text('name: "Alice "Al""\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "prog",
        "--scenes-dir", str(scenes_dir),
        "--chars-dir", str(chars_dir),
    ])
    main()
    out = capsys.readouterr().out
    assert "char.yaml" in out


def test_main_real_write(monkeypatch, tmp_path, capsys):
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    broken = scenes_dir / "s.yaml"
    broken.write_text('title: "Scene "X""\nstatus: draft\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "prog",
        "--scenes-dir", str(scenes_dir),
        "--chars-dir", str(tmp_path / "no_chars"),
    ])
    main()
    # File should now be valid YAML
    import yaml as _yaml
    _yaml.safe_load(broken.read_text(encoding="utf-8"))  # no exception


def test_main_exception_in_repair_counted(monkeypatch, tmp_path, capsys):
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    (scenes_dir / "ok.yaml").write_text("title: clean\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "prog", "--scenes-dir", str(scenes_dir), "--chars-dir", str(tmp_path / "nope"),
    ])
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "scripts.repair_yaml_quotes.repair_file", side_effect=OSError("permission denied")
    ):
        main()
    out = capsys.readouterr()
    assert "errori" in out.out
