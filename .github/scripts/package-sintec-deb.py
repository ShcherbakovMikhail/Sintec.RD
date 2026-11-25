#!/usr/bin/env python3
"""Brand the upstream DEB without changing its runtime paths or service hooks."""

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile


def brand_package(root):
    control = root / "DEBIAN/control"
    content = control.read_text(encoding="utf-8")
    if not re.search(r"^Package: rustdesk$", content, re.MULTILINE):
        raise ValueError("Expected an unmodified upstream rustdesk package")
    for field, value in (
        ("Package", "sintec-rd"),
        ("Homepage", "https://github.com/ShcherbakovMikhail/Sintec.RD"),
        ("Description", "Sintec.RD remote desktop client, based on RustDesk."),
    ):
        content, count = re.subn(r"^" + field + r":.*$", field + ": " + value,
                                 content, flags=re.MULTILINE)
        if count != 1:
            raise ValueError("Missing or duplicate DEB field: " + field)
    # Both packages own rustdesk's paths, service and URI handler.
    content = content.rstrip() + "\nConflicts: rustdesk\nReplaces: rustdesk\n"
    control.write_text(content, encoding="utf-8")
    for filename in ("rustdesk.desktop", "rustdesk-link.desktop"):
        path = root / "usr/share/applications" / filename
        content = path.read_text(encoding="utf-8")
        if "Name=RustDesk\n" not in content:
            raise ValueError("Missing expected desktop branding: " + filename)
        path.write_text(content.replace("Name=RustDesk\n", "Name=Sintec.RD\n"),
                        encoding="utf-8")
    service = root / "usr/share/rustdesk/files/systemd/rustdesk.service"
    content = service.read_text(encoding="utf-8")
    if "Description=RustDesk\n" not in content:
        raise ValueError("Missing expected service branding")
    service.write_text(content.replace("Description=RustDesk\n", "Description=Sintec.RD\n"),
                       encoding="utf-8")
    checksums = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] == "DEBIAN" or path.is_symlink() or not path.is_file():
            continue
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        checksums.append(digest + "  " + relative.as_posix() + "\n")
    (root / "DEBIAN/md5sums").write_text("".join(checksums), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    with tempfile.TemporaryDirectory(prefix="sintec-deb-") as temporary:
        root = Path(temporary) / "package"
        subprocess.run(["dpkg-deb", "--raw-extract", str(args.source), str(root)], check=True)
        brand_package(root)
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(args.output)],
                       check=True)


if __name__ == "__main__":
    main()
