#!/usr/bin/env python3
"""
Enterprise Agentic SDLC Orchestrator CLI (`aew`).
Coordinates task planning, worktree isolation, coder agent execution,
consensus audit, QA verification, and merge landing.
"""

import argparse
import sys
import subprocess
from pathlib import Path

from .worktree import WorktreeManager
from .provider_pool import CLIProviderPool
from .consensus import ReviewAuditor
from .qa_runner import QAHarness


def cmd_status(args):
    """Inspect current workstation providers, worktrees, and health."""
    pool = CLIProviderPool()
    providers = pool.detect_available_clis()
    print("=" * 60)
    print("Agentic Enterprise Workstation (AEW) - Status")
    print("=" * 60)
    print("Discovered CLI Providers:")
    for p in providers:
        status_icon = "🟢 AVAILABLE" if p["available"] else "⚪ NOT INSTALLED"
        print(f"  [{p['name'].upper()}] - Role: {p['role']:<22} State: {status_icon}")
        if p["installed"]:
            print(f"      Path: {p['path']} (Model: {p['model']})")

    wt_mgr = WorktreeManager()
    worktrees = wt_mgr.list_worktrees()
    print(f"\nActive Worktrees ({len(worktrees)}):")
    for wt in worktrees:
        print(f"  • {wt.get('branch', 'detached')} -> {wt['path']}")
    print("=" * 60)


def cmd_run_mission(args):
    """Execute end-to-end task mission across coder, reviewer, and merger."""
    task_name = args.task
    branch = f"feat/{task_name}"
    print(f"\n[1/5] Initializing mission '{task_name}' on branch '{branch}'...")

    wt_mgr = WorktreeManager()
    worktree_path = wt_mgr.create_worktree(branch)
    print(f"  -> Isolated worktree created: {worktree_path}")

    # Provider selection
    pool = CLIProviderPool()
    coder_provider = pool.select_provider_for_role("primary-coder")
    reviewer_provider = pool.select_provider_for_role("adversarial-reviewer")
    print(f"[2/5] Assigned Providers:")
    print(f"  -> Coder:    {coder_provider['name'] if coder_provider else 'Simulated Native Agent'} ({coder_provider['model'] if coder_provider else 'default'})")
    print(f"  -> Reviewer: {reviewer_provider['name'] if reviewer_provider else 'Simulated Auditor'} ({reviewer_provider['model'] if reviewer_provider else 'default'})")

    # Step 3: Run Coder Task (write feature file)
    print(f"[3/5] Coder executing task in isolated worktree...")
    feature_file = worktree_path / f"{task_name}.py"
    if not feature_file.exists():
        feature_file.write_text(f'"""Automated module for {task_name}"""\n\ndef run():\n    return "OK: {task_name}"\n')
    
    # Commit changes in worktree
    subprocess.run(["git", "add", "."], cwd=str(worktree_path), check=True)
    subprocess.run(["git", "commit", "-m", f"feat: implement {task_name}"], cwd=str(worktree_path), check=True)
    print(f"  -> Coder committed step to branch '{branch}'.")

    # Step 4: Adversarial Review & Security Audit Gate
    print(f"[4/5] Executing Dual-Model Consensus & AST Audit...")
    auditor = ReviewAuditor()
    audit_res = auditor.audit_worktree(worktree_path)
    if not audit_res["passed"]:
        print("  ❌ Consensus Audit FAILED:")
        for r in audit_res["results"]:
            for f in r.get("findings", []):
                print(f"     [{f['severity']}] {f['file']}: {f['message']}")
        sys.exit(1)
    print(f"  -> Passed audit cleanly ({audit_res['audited_count']} files verified).")

    # Step 5: Merge landing
    print(f"[5/5] Landing branch into main via automated fast-forward merge...")
    subprocess.run(["git", "checkout", "main"], cwd=str(wt_mgr.repo_root), check=True)
    merge_proc = subprocess.run(["git", "merge", branch, "--no-edit"], cwd=str(wt_mgr.repo_root), capture_output=True, text=True)
    if merge_proc.returncode != 0:
        print(f"  ❌ Merge failed: {merge_proc.stderr}")
        sys.exit(1)
    
    # Prune worktree
    wt_mgr.remove_worktree(branch)
    print(f"  ✅ Branch '{branch}' successfully landed into main. Worktree cleaned up.")


def main():
    parser = argparse.ArgumentParser(prog="aew", description="Agentic Enterprise Workstation Orchestrator")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Inspect agent providers and active worktrees")
    p_status.set_defaults(func=cmd_status)

    # mission
    p_mission = subparsers.add_parser("mission", help="Execute an autonomous task mission with consensus gating")
    p_mission.add_argument("task", help="Name or slug of task")
    p_mission.set_defaults(func=cmd_run_mission)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
