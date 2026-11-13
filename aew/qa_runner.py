#!/usr/bin/env python3
"""
Enterprise QA Test Harness & Static Checks.
Runs unit tests, linting simulation, and branch health verification.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any


class QAHarness:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def run_unit_tests(self) -> Dict[str, Any]:
        """Execute test suites via unittest."""
        cmd = ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]
        proc = subprocess.run(cmd, cwd=str(self.root_dir), capture_output=True, text=True)
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }

    def verify_git_cleanliness(self) -> bool:
        """Verify no uncommitted garbage or index conflicts."""
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(self.root_dir),
            capture_output=True,
            text=True,
        )
        # Check that no unstaged changes remain outside ignored files
        return len(proc.stdout.strip()) == 0
