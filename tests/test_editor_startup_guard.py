"""Inert fixtures for repository-controlled editor startup source screening.

These tests never execute task commands or font assets.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_editor_startup_source import scan


class EditorStartupSourceGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def put_text(self, name: str, content: str) -> None:
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def put_bytes(self, name: str, content: bytes) -> None:
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def test_inert_main_settings_and_font_signature_are_allowed(self) -> None:
        self.put_text(".vscode/settings.json", '{"task.allowAutomaticTasks": "off"}')
        self.put_text(".vscode/tasks.json", '{"tasks": []}')
        vetted = Path(__file__).resolve().parents[1] / "public/fonts/fa-solid-900.woff2"
        self.put_bytes("public/fonts/fa-solid-900.woff2", vetted.read_bytes())
        self.assertEqual(scan(self.root), [])

    def test_folder_open_task_and_nested_workspace_are_rejected(self) -> None:
        self.put_text(".vscode/tasks.json", '{"runOptions": {"runOn": "folderOpen"}}')
        self.put_text("nested/workspace.code-workspace", r'{"runOn":"folder\u004fpen"}')
        findings = scan(self.root)
        self.assertEqual(sum("folder-open" in finding for finding in findings), 2)

    def test_case_variants_cannot_bypass_cross_platform_guard(self) -> None:
        self.put_text(".VSCODE/tasks.json", '{"runOn":"folderOpen"}')
        self.put_text("nested/evil.CODE-WORKSPACE", '{"runOn":"folderOpen"}')
        findings = scan(self.root)
        self.assertEqual(sum("folder-open" in finding for finding in findings), 2)

    def test_auto_consent_is_rejected_but_explicit_off_is_allowed(self) -> None:
        self.put_text(".vscode/settings.json", '{"task.allowAutomaticTasks": true}')
        self.assertTrue(any("automatic task consent" in finding for finding in scan(self.root)))
        self.put_text(".vscode/settings.json", '{"task.allowAutomaticTasks": "on"}')
        self.assertTrue(any("automatic task consent" in finding for finding in scan(self.root)))
        self.put_text(".vscode/settings.json", '{"task.allowAutomaticTasks": "off"}')
        self.assertEqual(scan(self.root), [])

    def test_disguised_font_code_and_unknown_extension_are_rejected(self) -> None:
        self.put_bytes("public/fonts/fa-solid-500.woff2", b"console.log('inert fixture')")
        self.put_text("public/fonts/fa-solid.lkf", "inert fixture")
        findings = scan(self.root)
        self.assertTrue(any("unreviewed font asset" in finding for finding in findings))
        self.assertTrue(any("unexpected font extension" in finding for finding in findings))

    def test_font_magic_polyglot_and_modified_pinned_asset_are_rejected(self) -> None:
        self.put_bytes("public/fonts/fa-solid-900.woff2", b"wOF2:console.log('not executed')")
        self.put_bytes("public/fonts/fa-solid-500.woff2", b"wOF2:inert polyglot")
        findings = scan(self.root)
        self.assertTrue(any("font digest mismatch" in finding for finding in findings))
        self.assertTrue(any("unreviewed font asset" in finding for finding in findings))

    def test_svg_git_windows_crlf_checkout_is_canonical_but_edits_are_not(self) -> None:
        vetted = Path(__file__).resolve().parents[1] / "public/fonts/fa-solid-900.svg"
        original = vetted.read_bytes()
        self.assertIn(b"\n", original)
        self.put_bytes(
            "public/fonts/fa-solid-900.svg",
            original.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"),
        )
        self.assertEqual(scan(self.root), [])
        self.put_bytes("public/fonts/fa-solid-900.svg", original + b"\n<!-- inert mutation -->")
        self.assertTrue(any("font digest mismatch" in finding for finding in scan(self.root)))

    def test_symlink_editor_file_is_rejected(self) -> None:
        self.put_text("target.txt", "inert")
        link = self.root / ".vscode" / "tasks.json"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(self.root / "target.txt")
        except (OSError, NotImplementedError):
            self.skipTest("unprivileged symlink unavailable")
        self.assertTrue(any("symbolic link" in finding for finding in scan(self.root)))


if __name__ == "__main__":
    unittest.main()
