#!/usr/bin/env python3
"""
Enterprise Git Worktree Lifecycle Manager.
Provides isolated workspaces for concurrent agents to prevent cross-contamination.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional


class WorktreeManager:
    def __init__(self, repo_root: Optional[str] = None):
        if repo_root is None:
            res = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.repo_root = Path(res.stdout.strip())
        else:
            self.repo_root = Path(repo_root).resolve()
        
        self.worktrees_dir = self.repo_root / ".worktrees"
        self.worktrees_dir.mkdir(exist_ok=True)

    def create_worktree(self, branch_name: str, base_ref: str = "HEAD") -> Path:
        """Create a dedicated git worktree for a branch."""
        target_path = self.worktrees_dir / branch_name.replace("/", "_")
        if target_path.exists():
            return target_path

        # Create branch & worktree
        cmd = [
            "git",
            "worktree",
            "add",
            "-b",
            branch_name,
            str(target_path),
            base_ref,
        ]
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Fallback if branch already exists
            cmd_existing = [
                "git",
                "worktree",
                "add",
                str(target_path),
                branch_name,
            ]
            fallback_res = subprocess.run(
                cmd_existing,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
            )
            if fallback_res.returncode != 0:
                raise RuntimeError(
                    f"Failed to create worktree: {result.stderr}\nFallback: {fallback_res.stderr}"
                )

        return target_path

    def remove_worktree(self, branch_name: str, force: bool = False) -> None:
        """Prune and remove an agent worktree."""
        target_path = self.worktrees_dir / branch_name.replace("/", "_")
        if target_path.exists():
            cmd = ["git", "worktree", "remove", str(target_path)]
            if force:
                cmd.append("--force")
            subprocess.run(cmd, cwd=str(self.repo_root), capture_output=True)
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(self.repo_root),
            capture_output=True,
        )

    def list_worktrees(self):
        """List active git worktrees."""
        res = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        worktrees = []
        current = {}
        for line in res.stdout.splitlines():
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line.split(" ", 1)[1]}
            elif line.startswith("branch "):
                current["branch"] = line.split(" ", 1)[1]
            elif line.startswith("HEAD "):
                current["head"] = line.split(" ", 1)[1]
        if current:
            worktrees.append(current)
        return worktrees
