"""Fail closed on tracked editor auto-execution and disguised font assets.

This inspects source bytes only. It never invokes an editor, task or asset.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

_FONT_EXTENSIONS = frozenset({
    ".css", ".eot", ".license", ".md", ".otf", ".svg",
    ".ttf", ".txt", ".woff", ".woff2",
})
_FONT_SIGNATURES = {
    ".otf": b"OTTO",
    ".ttf": b"\x00\x01\x00\x00",
    ".woff": b"wOFF",
    ".woff2": b"wOF2",
}
# Exact independently reviewed assets from clean main d02c99c. Updating a font
# requires an explicit source review and digest change; extension and four-byte
# signature checks alone cannot exclude script/font polyglots.
_PINNED_FONTS = {
    "fa-brands-400.eot": "811e1577184066108ceca86d5a624a9012303df5206c5cb0b27d5e3fedcba5a3",
    "fa-brands-400.svg": "02340ba1789d09bcc507563c89c4a847ba537bb8132082777a50519cf74bcb5b",
    "fa-brands-400.ttf": "a0c145382acfe59767d1487d6505f349665b685c2885cd91b621d141a292b0f8",
    "fa-brands-400.woff": "e836c5d5dfc13e18170c5bddefb4fdac7c65ac0ad43a4b431acdc4a98865a260",
    "fa-brands-400.woff2": "5d9190292acdd48ba0fc35080f7e7448f3cdf0d79199a4d23f0f49b5341fdf29",
    "fa-regular-400.eot": "01f4416f5db59e2dd6b6fbd9dc32336d99db18f7eb623a49f584d04afd279473",
    "fa-regular-400.svg": "865fd23de13b1920280e182359579e09eff7a09eb24676eceec7552838559f55",
    "fa-regular-400.ttf": "f32b94a29060dfec0c797a1dfe111357eb1d682f1aca4ac4b95cf0f4c3e2bfa9",
    "fa-regular-400.woff": "8e2d96198711b63752e5f2f5987b8ffc536df6156a065bdbe28cb7231cad793d",
    "fa-regular-400.woff2": "6a8c8e9e1e7f692c21af1956de163f3d026778e6449fe93a09a671847ca1ae65",
    "fa-solid-900.eot": "32501727bb23fc77615b1ec76b5f298ec22198c0f3d6a3e7d6fe4ac3cf315db9",
    "fa-solid-900.svg": "e768539808757f7eec20f09c9ee9b36b0e6c5636e90c9ee697995cbbc6ee0555",
    "fa-solid-900.ttf": "231d68cefbc6846fb78cafca8467401a4f371e226418662e8900e3d52adc00ab",
    "fa-solid-900.woff": "352f8ead280419dd953d2bc7843386bb9430e8152c2dbd2c2d2494f6b9567ee7",
    "fa-solid-900.woff2": "7f4d3fd0a705dbf8403298aad91d5de6972e6b5d536068eba8b24954a5a0a8c7",
}
_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
_AUTO_CONSENT = re.compile(r"[\"']?task\.allowautomatictasks[\"']?\s*:\s*")
_EXPLICIT_OFF = re.compile(r"(?:false|\"off\"|'off')\s*(?:[,}\r\n]|$)")


def _decoded_source(path: Path) -> str:
    source = path.read_text(encoding="utf-8", errors="replace")
    # Decode JSON escapes solely for inspection; do not parse or execute tasks.
    return _UNICODE_ESCAPE.sub(
        lambda match: chr(int(match.group(1), 16)), source,
    ).casefold()


def scan(root: Path) -> list[str]:
    """Return findings for suspicious tracked workspace startup surfaces."""
    issues: list[str] = []
    editor_files: set[Path] = set()
    # Inspect case-insensitively on every host: a path accepted by a Linux
    # runner may become an editor startup path on a Windows checkout.
    editor_dirs = {
        path for path in root.rglob("*") if path.name.casefold() == ".vscode"
    }
    for editor in sorted(editor_dirs):
        relative = editor.relative_to(root).as_posix()
        if editor.is_symlink():
            issues.append(f"{relative}: symbolic link is not permitted")
            continue
        if not editor.exists():
            continue
        for path in sorted(editor.rglob("*")):
            item = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(f"{item}: symbolic link is not permitted")
            elif path.is_file():
                editor_files.add(path)

    for workspace in (
        path for path in root.rglob("*")
        if path.name.casefold().endswith(".code-workspace")
    ):
        if workspace.is_symlink():
            issues.append(
                f"{workspace.relative_to(root).as_posix()}: symbolic link is not permitted"
            )
        elif workspace.is_file():
            editor_files.add(workspace)

    for path in sorted(editor_files):
        relative = path.relative_to(root).as_posix()
        source = _decoded_source(path)
        if "folderopen" in source:
            issues.append(f"{relative}: folder-open execution is forbidden")
        for consent in _AUTO_CONSENT.finditer(source):
            if not _EXPLICIT_OFF.match(source, consent.end()):
                issues.append(f"{relative}: automatic task consent is forbidden")

    public = root / "public"
    fonts = public / "fonts"
    if public.is_symlink():
        issues.append("public: symbolic link is not permitted")
    elif fonts.is_symlink():
        issues.append("public/fonts: symbolic link is not permitted")
    elif fonts.exists():
        for path in sorted(fonts.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(f"{relative}: symbolic link is not permitted")
            elif path.is_file():
                suffix = path.suffix.casefold()
                asset = path.relative_to(fonts).as_posix()
                if suffix not in _FONT_EXTENSIONS:
                    issues.append(f"{relative}: unexpected font extension")
                elif asset != "README.md" and asset not in _PINNED_FONTS:
                    issues.append(f"{relative}: unreviewed font asset")
                elif suffix in _FONT_SIGNATURES:
                    with path.open("rb") as stream:
                        signature = stream.read(4)
                    if signature != _FONT_SIGNATURES[suffix]:
                        issues.append(f"{relative}: invalid font signature")
                if asset in _PINNED_FONTS:
                    content = path.read_bytes()
                    # Git on Windows can checkout tracked SVGs as CRLF text.
                    # Normalize that transport-only difference; binary font
                    # signatures and digests remain byte-for-byte pinned.
                    if suffix == ".svg":
                        content = content.replace(b"\r\n", b"\n")
                    digest = hashlib.sha256(content).hexdigest()
                    if digest != _PINNED_FONTS[asset]:
                        issues.append(f"{relative}: font digest mismatch")
    return issues


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues = scan(root)
    for issue in issues:
        print(f"editor startup source guard: {issue}", file=sys.stderr)
    if issues:
        return 1
    print("editor startup source guard: PASS (source-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
