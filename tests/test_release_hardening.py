"""Release-hardening utility tests; no external network or model execution."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_offline  # noqa: E402
import write_lock  # noqa: E402


class DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ReleaseHardeningTests(unittest.TestCase):
    def test_canonical_package_name(self):
        self.assertEqual(write_lock.canonical("HTTPX2"), "httpx2")
        self.assertEqual(write_lock.canonical("some.package_Name"), "some-package-name")

    def test_lock_hash_is_line_ending_independent(self):
        lf = "alpha==1\nbeta==2\n"
        crlf = "alpha==1\r\nbeta==2\r\n"
        self.assertEqual(write_lock.text_sha256(lf), write_lock.text_sha256(crlf))

    def test_committed_lock_matches_metadata_canonically(self):
        lock_text = (ROOT / "requirements.lock.txt").read_text(encoding="utf-8")
        metadata = json.loads((ROOT / "docs" / "environment-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["lock_hash_mode"], "utf8-canonical-lf")
        self.assertEqual(write_lock.text_sha256(lock_text), metadata["lock_sha256"])

    def test_offline_gate_passes_only_when_all_probes_unreachable(self):
        with patch("check_offline.socket.create_connection", side_effect=OSError("offline")):
            results = check_offline.prove_external_network_unavailable()
        self.assertEqual(len(results), len(check_offline.EXTERNAL_PROBES))
        self.assertTrue(all(item["result"] == "unreachable" for item in results))

    def test_offline_gate_rejects_reachable_external_endpoint(self):
        with patch("check_offline.socket.create_connection", return_value=DummyConnection()):
            with self.assertRaises(RuntimeError):
                check_offline.prove_external_network_unavailable()

    def test_free_port_returns_valid_loopback_port(self):
        port = check_offline.free_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)


if __name__ == "__main__":
    unittest.main()
