import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "chatgpt"


def test_plugin_manifests_are_consistent_and_read_only() -> None:
    public = json.loads((PLUGIN_ROOT / "plugin.json").read_text())
    codex = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

    assert public["name"] == codex["name"] == "sql-connectome"
    assert public["version"] == codex["version"] == "0.1.0"

    public_caps = public["extensions"]["com.openai"]["interface"]["capabilities"]
    codex_caps = codex["interface"]["capabilities"]
    assert public_caps == codex_caps

    joined = " ".join(public_caps).lower()
    for forbidden in ("write", "delete", "drop", "restore", "migration apply"):
        assert forbidden not in joined


def test_plugin_skill_preserves_connection_and_authority_boundaries() -> None:
    skill = (PLUGIN_ROOT / "skills" / "sql-connectome" / "SKILL.md").read_text()

    assert "does not prove" in skill
    assert "UNDERSTAND != TRANSLATE != VALIDATE != EXECUTE != AUTHORIZE" in skill
    assert "no protected write tool" in skill
