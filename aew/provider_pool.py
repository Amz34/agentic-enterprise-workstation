#!/usr/bin/env python3
"""
CLI Provider Pool & Resilient Circuit Breaker.
Multiplexes over local developer subscriptions (Claude, Codex, Copilot, Grok, Hermes, Ollama).
Falls back gracefully when quotas or timeouts hit.
"""

import time
import shutil
from typing import List, Dict, Any, Optional


class ProviderCircuitBreaker:
    def __init__(self, failure_threshold: int = 2, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED (healthy), OPEN (tripped), HALF-OPEN (testing)

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def is_available(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                return True
            return False
        return True  # HALF-OPEN allows probe request


class CLIProviderPool:
    DEFAULT_PROVIDERS = [
        {"name": "claude", "command": "claude", "role": "primary-coder", "model": "claude-3-7-sonnet"},
        {"name": "codex", "command": "codex", "role": "adversarial-reviewer", "model": "o3-mini"},
        {"name": "copilot", "command": "gh", "subcommand": ["copilot"], "role": "fallback-coder", "model": "gpt-4o"},
        {"name": "hermes", "command": "hermes", "role": "self-hosted", "model": "hermes-3-llama-3.1-70b"},
        {"name": "ollama", "command": "ollama", "role": "local-fallback", "model": "qwen2.5-coder:32b"},
    ]

    def __init__(self, custom_providers: Optional[List[Dict[str, Any]]] = None):
        self.providers = custom_providers or self.DEFAULT_PROVIDERS
        self.breakers = {
            p["name"]: ProviderCircuitBreaker() for p in self.providers
        }

    def detect_available_clis(self) -> List[Dict[str, Any]]:
        """Probe the host machine for installed and accessible CLI binaries."""
        available = []
        for p in self.providers:
            cmd = p["command"]
            bin_path = shutil.which(cmd)
            is_installed = bin_path is not None
            is_healthy = self.breakers[p["name"]].is_available()
            available.append({
                "name": p["name"],
                "command": cmd,
                "role": p["role"],
                "model": p["model"],
                "installed": is_installed,
                "path": bin_path,
                "circuit_state": self.breakers[p["name"]].state,
                "available": is_installed and is_healthy,
            })
        return available

    def select_provider_for_role(self, role: str) -> Optional[Dict[str, Any]]:
        """Select healthy provider matching role with graceful fallback."""
        candidates = [
            p for p in self.detect_available_clis()
            if p["available"] and (role in p["role"] or p["role"] == "local-fallback")
        ]
        if candidates:
            return candidates[0]
        # Fallback to any available provider
        any_avail = [p for p in self.detect_available_clis() if p["available"]]
        return any_avail[0] if any_avail else None
