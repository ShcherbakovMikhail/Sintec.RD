import hashlib
import importlib.util
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("package-sintec-deb.py")
spec = importlib.util.spec_from_file_location("sintec_deb", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
REPOSITORY = SCRIPT.parents[2]


class DebPackagingTests(unittest.TestCase):
    def fixture(self, root):
        (root / "DEBIAN").mkdir(parents=True)
        (root / "DEBIAN/control").write_text(
            "Package: rustdesk\nVersion: 1.5.3\nArchitecture: amd64\n"
            "Maintainer: rustdesk <info@rustdesk.com>\nHomepage: https://rustdesk.com\n"
            "Depends: libgtk-3-0\nDescription: A remote control software.\n")
        for relative in (
            "usr/share/applications/rustdesk.desktop",
            "usr/share/applications/rustdesk-link.desktop",
            "usr/share/rustdesk/files/systemd/rustdesk.service",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPOSITORY / "res" / path.name, path)
        for name in ("preinst", "postinst", "prerm", "postrm"):
            shutil.copy2(REPOSITORY / "res/DEBIAN" / name, root / "DEBIAN" / name)

    def test_branding_preserves_dependencies_and_install_hooks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            module.brand_package(root)
            control = (root / "DEBIAN/control").read_text()
            self.assertIn("Package: sintec-rd\n", control)
            self.assertIn("Depends: libgtk-3-0\n", control)
            self.assertIn("Conflicts: rustdesk\nReplaces: rustdesk\n", control)
            desktop = (root / "usr/share/applications/rustdesk.desktop").read_text()
            self.assertIn("Name=Sintec.RD\n", desktop)
            self.assertIn("Exec=rustdesk %u\n", desktop)
            service = (root / "usr/share/rustdesk/files/systemd/rustdesk.service").read_text()
            self.assertIn("Description=Sintec.RD\n", service)
            self.assertIn("ExecStart=/usr/bin/rustdesk --service\n", service)
            for name in ("preinst", "postinst", "prerm", "postrm"):
                self.assertEqual((root / "DEBIAN" / name).read_bytes(),
                                 (REPOSITORY / "res/DEBIAN" / name).read_bytes())
            for line in (root / "DEBIAN/md5sums").read_text().splitlines():
                digest, relative = line.split("  ", 1)
                self.assertEqual(digest, hashlib.md5((root / relative).read_bytes()).hexdigest())

    def test_refuses_unexpected_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            (root / "DEBIAN/control").write_text("Package: other\n")
            with self.assertRaises(ValueError):
                module.brand_package(root)

    @unittest.skipUnless(shutil.which("dpkg-deb"), "requires Debian packaging tools")
    def test_cli_builds_installable_archive(self):
        # Build/extract only: never install or execute the package's service hooks.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "package"
            self.fixture(root)
            source, output = directory / "source.deb", directory / "sintec.deb"
            subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(source)],
                           check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["python3", str(SCRIPT), str(source), str(output)], check=True)
            fields = subprocess.check_output(["dpkg-deb", "--field", str(output)],
                                             universal_newlines=True)
            self.assertIn("Package: sintec-rd\n", fields)
            self.assertIn("Architecture: amd64\n", fields)


if __name__ == "__main__":
    unittest.main()
