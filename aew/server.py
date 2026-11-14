#!/usr/bin/env python3
"""
AEW Web Cockpit & Control Plane.
FastAPI + HTML/WebSocket dashboard providing real-time views into worktrees,
mission pipelines, quota states, and episodic memory.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import json

from .provider_pool import CLIProviderPool
from .worktree import WorktreeManager
from .memory import MemoryStore

app = FastAPI(title="AEW Agentic Cockpit", version="0.1.0")
pool = CLIProviderPool()
wt_mgr = WorktreeManager()
memory = MemoryStore()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AEW Enterprise Cockpit</title>
    <style>
        :root { --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #c9d1d9; --accent: #58a6ff; --green: #238636; --red: #da3633; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; }
        h1, h2 { color: #f0f6fc; margin-top: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 18px; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
        .badge-green { background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid #238636; }
        .badge-red { background: rgba(218, 54, 51, 0.2); color: #f85149; border: 1px solid #da3633; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--border); }
        th { color: #8b949e; }
        pre { background: #000; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 12px; }
    </style>
</head>
<body>
    <header style="margin-bottom: 24px;">
        <h1>⚡ Agentic Enterprise Workstation (AEW)</h1>
        <p style="color: #8b949e;">Local Subscriptions · Dynamic Worktrees · Dual-Model Consensus · GitHub PR Governance</p>
    </header>

    <div class="grid">
        <div class="card">
            <h2>🔌 Provider Pool & Quota Circuit</h2>
            <div id="providers-container">Loading...</div>
        </div>
        <div class="card">
            <h2>🌿 Active Worktree Sandboxes</h2>
            <div id="worktrees-container">Loading...</div>
        </div>
    </div>

    <div class="grid" style="margin-top: 20px;">
        <div class="card">
            <h2>📜 Recent Missions</h2>
            <div id="missions-container">Loading...</div>
        </div>
        <div class="card">
            <h2>🧠 Episodic Rules & Architectural Memory</h2>
            <div id="rules-container">Loading...</div>
        </div>
    </div>

    <script>
        async function refreshData() {
            try {
                const res = await fetch('/api/state');
                const data = await res.json();
                
                // Render Providers
                let p_html = '<table><tr><th>Provider</th><th>Role</th><th>Model</th><th>Circuit</th></tr>';
                data.providers.forEach(p => {
                    const badge = p.available ? '<span class="badge badge-green">HEALTHY</span>' : '<span class="badge badge-red">OFFLINE</span>';
                    p_html += `<tr><td><strong>${p.name.toUpperCase()}</strong></td><td>${p.role}</td><td>${p.model}</td><td>${badge}</td></tr>`;
                });
                p_html += '</table>';
                document.getElementById('providers-container').innerHTML = p_html;

                // Render Worktrees
                let wt_html = '<table><tr><th>Branch</th><th>Path</th></tr>';
                data.worktrees.forEach(wt => {
                    wt_html += `<tr><td><code>${wt.branch || 'detached'}</code></td><td><small>${wt.path}</small></td></tr>`;
                });
                wt_html += '</table>';
                document.getElementById('worktrees-container').innerHTML = wt_html;

                // Render Missions
                let m_html = '<table><tr><th>ID</th><th>Task</th><th>Status</th></tr>';
                data.missions.forEach(m => {
                    m_html += `<tr><td><code>${m.id}</code></td><td>${m.task_name}</td><td><span class="badge badge-green">${m.status}</span></td></tr>`;
                });
                m_html += '</table>';
                document.getElementById('missions-container').innerHTML = m_html;

                // Render Rules
                let r_html = '<table><tr><th>Category</th><th>Rule</th></tr>';
                data.rules.forEach(r => {
                    r_html += `<tr><td><strong>${r.category}</strong></td><td>${r.rule_text}</td></tr>`;
                });
                r_html += '</table>';
                document.getElementById('rules-container').innerHTML = r_html;

            } catch (e) {
                console.error(e);
            }
        }
        refreshData();
        setInterval(refreshData, 5000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return DASHBOARD_HTML

@app.get("/api/state")
def get_state():
    return {
        "providers": pool.detect_available_clis(),
        "worktrees": wt_mgr.list_worktrees(),
        "missions": memory.get_recent_missions(10),
        "rules": memory.get_rules(),
    }
