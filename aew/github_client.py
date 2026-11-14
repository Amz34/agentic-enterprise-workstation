#!/usr/bin/env python3
"""
AEW GitHub Enterprise Automation Client.
Coordinates remote pushing, automated PR generation, adversarial review commenting, and auto-merge.
"""

import subprocess
import shutil
import json
from typing import Dict, Any, Optional


class GitHubEnterpriseClient:
    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir
        self.has_gh = shutil.which("gh") is not None

    def check_auth(self) -> Dict[str, Any]:
        """Check if gh CLI is authenticated with GitHub / GitHub Enterprise."""
        if not self.has_gh:
            return {"authenticated": False, "reason": "gh CLI binary not found"}
        res = subprocess.run(
            ["gh", "auth", "status"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True
        )
        is_auth = res.returncode == 0
        return {"authenticated": is_auth, "output": res.stdout or res.stderr}

    def push_branch(self, branch: str, remote: str = "origin") -> bool:
        """Push local branch to remote repository."""
        res = subprocess.run(
            ["git", "push", "-u", remote, branch],
            cwd=self.repo_dir,
            capture_output=True,
            text=True
        )
        return res.returncode == 0

    def create_pull_request(self, branch: str, title: str, body: str, base: str = "main") -> Dict[str, Any]:
        """Create pull request using gh CLI."""
        if not self.has_gh:
            return {"success": False, "error": "gh CLI not installed"}

        cmd = [
            "gh", "pr", "create",
            "--base", base,
            "--head", branch,
            "--title", title,
            "--body", body
        ]
        res = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True)
        if res.returncode == 0:
            pr_url = res.stdout.strip()
            return {"success": True, "url": pr_url}
        else:
            return {"success": False, "error": res.stderr}

    def comment_on_pr(self, pr_ref: str, comment: str) -> bool:
        """Add consensus review findings as a comment on the PR."""
        if not self.has_gh:
            return False
        cmd = ["gh", "pr", "comment", pr_ref, "--body", comment]
        res = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True)
        return res.returncode == 0

    def enable_auto_merge(self, pr_ref: str) -> bool:
        """Enable auto-merge once CI checks pass."""
        if not self.has_gh:
            return False
        cmd = ["gh", "pr", "merge", pr_ref, "--auto", "--squash"]
        res = subprocess.run(cmd, cwd=self.repo_dir, capture_output=True, text=True)
        return res.returncode == 0
