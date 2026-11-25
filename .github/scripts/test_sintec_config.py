import base64
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).with_name("check-sintec-config.py")
spec = importlib.util.spec_from_file_location("sintec_config", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuildSettingsTests(unittest.TestCase):
    def settings(self):
        return {
            "SINTEC_SERVER_ADDRESS": "rd.example.invalid:21116",
            "SINTEC_SERVER_PUBLIC_KEY": base64.b64encode(bytes(range(32))).decode(),
        }

    def test_accepts_host_and_public_key(self):
        module.validate(self.settings())

    def test_refuses_missing_or_invalid_settings(self):
        cases = [
            ("SINTEC_SERVER_ADDRESS", ""),
            ("SINTEC_SERVER_ADDRESS", "https://rd.example.invalid"),
            ("SINTEC_SERVER_ADDRESS", " host "),
            ("SINTEC_SERVER_PUBLIC_KEY", ""),
            ("SINTEC_SERVER_PUBLIC_KEY", "-----BEGIN PRIVATE KEY-----"),
            ("SINTEC_SERVER_PUBLIC_KEY", base64.b64encode(bytes(64)).decode()),
        ]
        for name, value in cases:
            with self.subTest(name=name, value_type="invalid"):
                settings = self.settings()
                settings[name] = value
                with self.assertRaises(ValueError):
                    module.validate(settings)

    def test_cli_fails_closed_without_logging_values(self):
        settings = self.settings()
        environment = {**os.environ, **settings}
        valid = subprocess.run([sys.executable, str(SCRIPT)], env=environment,
                               capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0)
        for value in settings.values():
            self.assertNotIn(value, valid.stdout + valid.stderr)
        environment["SINTEC_SERVER_PUBLIC_KEY"] = "DO_NOT_LOG_THIS_PRIVATE_VALUE"
        invalid = subprocess.run([sys.executable, str(SCRIPT)], env=environment,
                                 capture_output=True, text=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertNotIn(environment["SINTEC_SERVER_PUBLIC_KEY"],
                         invalid.stdout + invalid.stderr)


if __name__ == "__main__":
    unittest.main()
