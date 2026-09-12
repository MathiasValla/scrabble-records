#!/usr/bin/env python3
"""Verify a public or review snapshot against its versioned manifest."""
import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", default="RELEASE_MANIFEST.json")
    parser.add_argument("--require-dictionaries", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / args.manifest
    record = json.loads(manifest_path.read_text())
    assert record["schema"] == "release-manifest-v1"
    for relative, expected in record["files"].items():
        path = root / relative
        assert path.is_file(), f"missing: {relative}"
        actual = sha256(path)
        assert actual == expected, f"digest mismatch: {relative}"
    inputs_checked = 0
    for relative, expected in record["required_external_inputs"].items():
        path = root / relative
        if path.is_file():
            assert sha256(path) == expected, f"dictionary digest mismatch: {relative}"
            inputs_checked += 1
        elif args.require_dictionaries:
            raise AssertionError(f"missing required dictionary: {relative}")
    print(f"VERIFIED: {len(record['files'])} archived files; "
          f"{inputs_checked} external dictionaries present and matched.")


if __name__ == "__main__":
    main()
