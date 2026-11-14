#!/usr/bin/env python3
"""
AEW Live CLI Execution Runner.
Executes real commands inside worktrees, streams output to mission logs,
detects quota limits / errors, and triggers circuit breakers.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from .provider_pool import CLIProviderPool


class LiveAgentRunner:
    def __init__(self, provider_pool: CLIProviderPool):
        self.provider_pool = provider_pool

    def execute_coder_in_worktree(
        self,
        worktree_path: Path,
        prompt: str,
        role: str = "primary-coder",
        log_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute coding agent inside the isolated worktree directory.
        Checks for quota exhaustion and cascades through fallback providers.
        """
        provider = self.provider_pool.select_provider_for_role(role)
        if not provider:
            return {"success": False, "error": "No available CLI providers in pool"}

        if log_file is None:
            log_file = worktree_path / "agent_execution.log"

        cmd_name = provider["name"]
        binary_cmd = provider["command"]

        # Formulate non-interactive agent call based on detected CLI
        # e.g., claude --print / hermes -q / custom instruction wrapper
        if cmd_name == "claude":
            args = [binary_cmd, "--print", prompt]
        elif cmd_name == "copilot":
            args = ["gh", "copilot", "suggest", "-t", "shell", prompt]
        elif cmd_name == "ollama":
            args = [binary_cmd, "run", provider["model"], prompt]
        else:
            args = [binary_cmd, prompt]

        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"\n--- [AGENT DISPATCH: {cmd_name} ({provider['model']})] ---\n")
            lf.write(f"PROMPT: {prompt}\n\n")

            try:
                # Run with timeout to prevent hung processes
                proc = subprocess.run(
                    args,
                    cwd=str(worktree_path),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env={**os.environ, "CI": "true"}
                )
                output = proc.stdout + "\n" + proc.stderr
                lf.write(output)

                # Check for quota exhaustion indicators
                quota_indicators = ["quota exceeded", "rate limit reached", "insufficient credits", "429 too many requests"]
                if any(ind in output.lower() for ind in quota_indicators):
                    self.provider_pool.breakers[cmd_name].record_failure()
                    # Trigger fallback to next available provider
                    fallback_provider = self.provider_pool.select_provider_for_role(role)
                    if fallback_provider and fallback_provider["name"] != cmd_name:
                        lf.write(f"\n[CIRCUIT BREAKER TRIPPED for {cmd_name}] Cascading to {fallback_provider['name']}...\n")
                        return self.execute_coder_in_worktree(worktree_path, prompt, role, log_file)

                if proc.returncode == 0:
                    self.provider_pool.breakers[cmd_name].record_success()
                    return {
                        "success": True,
                        "provider": cmd_name,
                        "output": output,
                        "log_path": str(log_file)
                    }
                else:
                    return {
                        "success": False,
                        "provider": cmd_name,
                        "error": proc.stderr or proc.stdout,
                        "log_path": str(log_file)
                    }

            except subprocess.TimeoutExpired:
                self.provider_pool.breakers[cmd_name].record_failure()
                lf.write(f"\n[ERROR] Command timed out after 120s\n")
                return {"success": False, "provider": cmd_name, "error": "Timeout expired"}
            except Exception as e:
                self.provider_pool.breakers[cmd_name].record_failure()
                lf.write(f"\n[EXCEPTION] {str(e)}\n")
                return {"success": False, "provider": cmd_name, "error": str(e)}
