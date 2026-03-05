# Task 8.1 — Python Agent

**Time**: 6 hours  
**Dependencies**: Phase 6  
**Status**: ⬜ Not Started  
**Files**: `agent/`

---

## AI Prompt

```
Implement the PatchGuard agent — a lightweight Python daemon that runs on managed devices.

1. agent/agent.py — Main PatchAgent class:
   - WebSocket connection with exponential backoff reconnection
   - heartbeat_loop() — send system metrics every interval
   - message_handler() — route incoming commands
   - install_patches() — download, verify, install via OS plugin
   - scan_patches() — scan via OS plugin, report results
   - send_system_info() — report OS, hardware, agent version

2. agent/plugins/linux.py — LinuxPlugin (apt/yum/dnf)
3. agent/plugins/windows.py — WindowsPlugin (wusa/PowerShell)
4. agent/plugins/macos.py — MacOSPlugin (softwareupdate)
5. agent/config.yaml — Template configuration
6. agent/install.sh — Installation script (systemd service)

Write tests mocking WebSocket and subprocess.
```

---

## Acceptance Criteria

- [ ] Agent connects to FastAPI WebSocket
- [ ] Heartbeats send every configured interval
- [ ] System info reported on connect
- [ ] Patch install calls correct OS plugin
- [ ] Status updates sent during install lifecycle
- [ ] Reconnection with backoff works
- [ ] systemd service starts on boot
- [ ] All tests pass

## Files Created/Modified

- [ ] `agent/agent.py`
- [ ] `agent/plugins/linux.py`
- [ ] `agent/plugins/windows.py`
- [ ] `agent/plugins/macos.py`
- [ ] `agent/config.yaml`
- [ ] `agent/install.sh`
- [ ] `agent/requirements.txt`
- [ ] `agent/tests/`

## Completion Log

<!-- Record completion date, notes, and any deviations -->
