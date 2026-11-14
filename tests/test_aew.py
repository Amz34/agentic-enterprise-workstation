import unittest
import tempfile
import shutil
from pathlib import Path
from aew.consensus import ReviewAuditor
from aew.provider_pool import CLIProviderPool, ProviderCircuitBreaker
from aew.memory import MemoryStore
from aew.github_client import GitHubEnterpriseClient


class TestAEWSuite(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.auditor = ReviewAuditor()
        self.memory = MemoryStore(db_path=Path(self.test_dir) / "test_memory.db")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clean_python_code(self):
        code = "def add(a, b):\n    return a + b\n"
        res = self.auditor.audit_file_content("test.py", code)
        self.assertTrue(res["passed"])
        self.assertEqual(len(res["findings"]), 0)

    def test_syntax_error_detection(self):
        code = "def broken(\n"
        res = self.auditor.audit_file_content("bad.py", code)
        self.assertFalse(res["passed"])
        self.assertEqual(res["findings"][0]["type"], "SYNTAX_ERROR")

    def test_secret_leak_detection(self):
        code = 'AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        res = self.auditor.audit_file_content("config.py", code)
        self.assertFalse(res["passed"])
        self.assertEqual(res["findings"][0]["type"], "SECRET_LEAK")

    def test_circuit_tripping(self):
        cb = ProviderCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        self.assertTrue(cb.is_available())
        cb.record_failure()
        self.assertTrue(cb.is_available())
        cb.record_failure()
        self.assertFalse(cb.is_available())
        self.assertEqual(cb.state, "OPEN")

    def test_memory_persistence(self):
        self.memory.record_mission_start("m-001", "refactor-db", "feat/refactor-db", "claude", "codex")
        self.memory.add_rule("CONVENTION", "Always use type annotations", "m-001")
        self.memory.record_mission_end("m-001", "SUCCESS")

        rules = self.memory.get_rules("CONVENTION")
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["rule_text"], "Always use type annotations")

        missions = self.memory.get_recent_missions(5)
        self.assertEqual(len(missions), 1)
        self.assertEqual(missions[0]["status"], "SUCCESS")

    def test_github_client_instantiation(self):
        client = GitHubEnterpriseClient(self.test_dir)
        self.assertTrue(client.has_gh)


if __name__ == "__main__":
    unittest.main()
