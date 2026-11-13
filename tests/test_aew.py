import unittest
import tempfile
import shutil
from pathlib import Path
from aew.consensus import ReviewAuditor
from aew.provider_pool import CLIProviderPool, ProviderCircuitBreaker
from aew.worktree import WorktreeManager


class TestConsensusAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = ReviewAuditor()

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


class TestProviderCircuitBreaker(unittest.TestCase):
    def test_circuit_tripping(self):
        cb = ProviderCircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        self.assertTrue(cb.is_available())
        cb.record_failure()
        self.assertTrue(cb.is_available())
        cb.record_failure()
        # Should now be tripped (OPEN)
        self.assertFalse(cb.is_available())
        self.assertEqual(cb.state, "OPEN")


if __name__ == "__main__":
    unittest.main()
