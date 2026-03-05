# Task 8.1 — Python Agent

**Time**: 6 hours  
**Dependencies**: Phase 6  
**Status**: ✅ Completed
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

- [x] Agent connects to FastAPI WebSocket
- [x] Heartbeats send every configured interval
- [x] System info reported on connect
- [x] Patch install calls correct OS plugin
- [x] Status updates sent during install lifecycle
- [x] Reconnection with backoff works
- [x] systemd service starts on boot
- [x] All tests pass

## Files Created/Modified

- [x] `agent/agent.py`
- [x] `agent/plugins/linux.py`
- [x] `agent/plugins/windows.py`
- [x] `agent/plugins/macos.py`
- [x] `agent/config.yaml`
- [x] `agent/install.sh`
- [x] `agent/requirements.txt`
- [x] `agent/plugins/base.py`

## Completion Log

- **2026-04-05**: Fully implemented the PatchGuard Agent. Includes a core asynchronous loop in `agent.py` for WebSocket-based communication and telemetry collection. Cross-platform support is achieved through a plugin architecture for Windows, Linux (apt/yum), and macOS. systemd registration is supported via `install.sh`.
