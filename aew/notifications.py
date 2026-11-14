#!/usr/bin/env python3
"""
AEW Enterprise Webhook & Notification Dispatcher.
Supports Slack, Microsoft Teams, and Discord webhooks with graceful no-op fallbacks.
"""

import os
import json
import urllib.request
from typing import Dict, Any, Optional


class NotificationDispatcher:
    def __init__(self):
        self.slack_webhook = os.getenv("AEW_SLACK_WEBHOOK") or os.getenv("SLACK_WEBHOOK_URL")
        self.teams_webhook = os.getenv("AEW_TEAMS_WEBHOOK") or os.getenv("TEAMS_WEBHOOK_URL")
        self.discord_webhook = os.getenv("AEW_DISCORD_WEBHOOK") or os.getenv("DISCORD_WEBHOOK_URL")

    def has_configured_webhooks(self) -> bool:
        return bool(self.slack_webhook or self.teams_webhook or self.discord_webhook)

    def dispatch_alert(self, title: str, message: str, level: str = "INFO", fields: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send notification payload across all active webhooks.
        Level: INFO, SUCCESS, WARNING, CRITICAL
        """
        results = {}
        color_map = {
            "INFO": "#58a6ff",
            "SUCCESS": "#238636",
            "WARNING": "#d29922",
            "CRITICAL": "#da3633",
        }
        color = color_map.get(level.upper(), "#58a6ff")

        # 1. Slack Webhook Dispatch
        if self.slack_webhook:
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{level}] {title}",
                        "text": message,
                        "fields": [{"title": k, "value": v, "short": True} for k, v in (fields or {}).items()],
                    }
                ]
            }
            results["slack"] = self._send_json(self.slack_webhook, payload)

        # 2. Discord Webhook Dispatch
        if self.discord_webhook:
            payload = {
                "embeds": [
                    {
                        "title": f"[{level}] {title}",
                        "description": message,
                        "color": int(color.lstrip("#"), 16),
                        "fields": [{"name": k, "value": v, "inline": True} for k, v in (fields or {}).items()],
                    }
                ]
            }
            results["discord"] = self._send_json(self.discord_webhook, payload)

        # 3. MS Teams Webhook Dispatch
        if self.teams_webhook:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color.lstrip("#"),
                "summary": title,
                "sections": [
                    {
                        "activityTitle": f"[{level}] {title}",
                        "activitySubtitle": message,
                        "facts": [{"name": k, "value": v} for k, v in (fields or {}).items()],
                    }
                ],
            }
            results["teams"] = self._send_json(self.teams_webhook, payload)

        return results

    def _send_json(self, url: str, data: Dict[str, Any]) -> bool:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False
