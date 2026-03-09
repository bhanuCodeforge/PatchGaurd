# PatchGuard — Pending Production Release Tasks

> **Source of truth**: `docs/UserManual/patchguard-user-guide.md` + `tasks/` phase files  
> **Last audited**: 2026-04-09 (second pass — 16 new gaps discovered)  
> **Purpose**: Track missing work before production sign-off  
> **Total gaps**: 23 (7 previously tracked + 16 new)

---

## 🔴 Blockers (must complete before release)

### 1) Deployment approval workflow UI completion (§7.8)
- [ ] Add **Approve** action in deployment list/details for Admin role only
- [ ] Show clear **Awaiting Approval** status for draft deployments when approval is required
- [ ] Validate role behavior: Operator can create draft; only Admin can approve
- [ ] Add e2e coverage for draft → approve → scheduled/in-progress flow

**Owner**: Frontend + Backend  
**Refs**: `frontend/src/app/features/deployments/`, `backend/apps/deployments/views.py`

### 2) Pre-flight health checks in real wave execution (§7.6.2)
- [ ] Replace placeholder/simulated preflight wait with real result-driven flow
- [ ] Skip unhealthy targets per wave and retry in later wave (or explicitly fail with reason)
- [ ] Persist and expose preflight result per target in API and live monitor
- [ ] Add tests for unhealthy devices not being patched in active wave

**Owner**: Backend (Celery + Deployments)  
**Refs**: `backend/apps/deployments/tasks.py`

### 3) Bulk patch reject in UI (§6.11)
- [ ] Add **Bulk Reject** action in patch catalog (bulk approve already exists)
- [ ] Use selected-row IDs and submit reason where required
- [ ] Show success/error summary for bulk results

**Owner**: Frontend  
**Refs**: `frontend/src/app/features/patches/patch-catalog.component.*`

---

## 🟠 High priority (release quality)

### 4) Advanced system settings — Admin pages (§13.1–13.9) *(expanded)*
- [ ] **General settings** (§13.1): Organization name, timezone, session timeout, require deployment approval toggle, SLA windows
- [ ] **Vendor feed config** (§13.2): Feed URLs, sync intervals, auto-import, manual "Sync now" button
- [ ] **Notification settings** (§13.3): Channel toggles for critical patches, deployment failures, device offline, compliance threshold
- [ ] **Email / SMTP config** (§13.4): server, port, TLS, credentials, from address, "Send test email"
- [ ] **Webhook alerts config** (§13.4): URL, test POST, Slack / Teams / PagerDuty compatible
- [ ] **Maintenance window presets** (§13.5): Name, cron/schedule, duration, timezone
- [ ] **Data retention policies** (§13.6): Configurable retention per data type (audit, deploy history, metrics, decommissioned)
- [ ] **TLS certificate management** (§13.7): View issuer/expiry/fingerprint, upload new cert+key, 30-day expiry warning
- [ ] **Backup & restore** (§13.8): Backup scheduling, "Backup now" button, restore instructions
- [ ] **System health check dashboard** (§13.9): PostgreSQL, Redis, Celery, WebSocket, disk status indicators

**Owner**: Frontend + Backend  
**Refs**: `frontend/src/app/features/settings/`, `backend/config/settings/`, `realtime/routes/health.py`

### 5) SLA reporting detail output (§9.7)
- [ ] Extend compliance/report API to return detailed SLA breach rows
- [ ] Include patch identifier, severity, overdue duration, and affected count
- [ ] Render SLA breach table in frontend compliance/report views

**Owner**: Backend + Frontend  
**Refs**: `backend/apps/deployments/views.py`, `frontend/src/app/features/compliance/`

### 6) Report export — compliance & audit (§9.8, §10.5) 🆕
- [ ] Add **Export** button on compliance dashboard (CSV, PDF, JSON)
- [ ] Backend endpoints to generate compliance export files
- [ ] Add **Export** button on audit log page (CSV, JSON)
- [ ] Backend endpoint to stream/download filtered audit entries
- [ ] PDF export formatted for printing / change management records

**Owner**: Frontend + Backend  
**Refs**: `frontend/src/app/features/compliance/`, `frontend/src/app/features/audit-log/`, `backend/apps/deployments/views.py`

### 7) Device data export (§4.16) 🆕
- [ ] Implement export service for device list (CSV, JSON, PDF)
- [ ] Backend export endpoint respecting current filters
- [ ] Wire existing "Export" button in device list to actual download

**Owner**: Frontend + Backend  
**Refs**: `frontend/src/app/features/devices/devices-list/device-list.component.*`, `backend/apps/inventory/views.py`

---

## 🟡 Medium priority (feature completeness)

### 8) Keyboard shortcuts (§2.3) 🆕
- [ ] Implement global key listener: `G+D` (Dashboard), `G+V` (Devices), `G+P` (Patches), `G+E` (Deployments)
- [ ] `/` focuses search bar, `Esc` closes modal/goes back, `?` shows shortcut help overlay
- [ ] Add shortcuts help modal accessible from `?` key

**Owner**: Frontend  
**Refs**: `frontend/src/app/layout/`, `frontend/src/app/app.component.ts`

### 9) Responsive sidebar collapse (§2.5) 🆕
- [ ] At `<900px` sidebar collapses to hamburger menu
- [ ] Dashboard KPI cards stack to 2 columns
- [ ] Detail views switch to single-column layout

**Owner**: Frontend  
**Refs**: `frontend/src/app/layout/sidebar/`, `frontend/src/styles.scss`

### 10) Dark mode auto-detect (§2.4) 🆕
- [ ] Use `prefers-color-scheme` CSS media query to auto-follow OS theme
- [ ] Apply dark/light theme variables across all components
- [ ] No manual toggle required — seamless OS-based switching

**Owner**: Frontend  
**Refs**: `frontend/src/styles.scss`, component SCSS files

### 11) Device activity log tab (§4.8) 🆕
- [ ] Add "Activity Log" tab in device detail view
- [ ] Show timestamped chronological events: heartbeats, patch installs, scans, agent updates, connect/disconnect
- [ ] Colored dots per event type (blue=info, green=success, red=error, amber=warning)
- [ ] Display last 50 events; link to full audit log

**Owner**: Frontend + Backend  
**Refs**: `frontend/src/app/features/devices/device-full-detail/`, `backend/apps/inventory/views.py`

### 12) Nested device group hierarchies (§5.6) 🆕
- [ ] Add `parent_group` FK to DeviceGroup model
- [ ] Parent group membership includes all children's devices
- [ ] Group CRUD UI: parent selector in create/edit form
- [ ] Hierarchical display in group list (tree or indented)

**Owner**: Backend + Frontend  
**Refs**: `backend/apps/inventory/models.py`, `frontend/src/app/features/devices/group-list/`

### 13) Per-group compliance breakdown (§9.4) 🆕
- [ ] Add API endpoint returning aggregate compliance rate per device group
- [ ] Render group compliance table in compliance dashboard
- [ ] Identify lowest-compliance groups for action

**Owner**: Backend + Frontend  
**Refs**: `backend/apps/deployments/views.py`, `frontend/src/app/features/compliance/`

### 14) Agent API key rotation (§11.9) 🆕
- [ ] Backend endpoint to rotate device agent API key (old key immediately invalidated)
- [ ] "Rotate API key" button in device detail settings tab
- [ ] Show new key in copy-able dialog; warn that agent config must be updated

**Owner**: Backend + Frontend  
**Refs**: `backend/apps/inventory/models.py`, `backend/apps/inventory/views.py`, `frontend/src/app/features/devices/device-full-detail/`

### 15) Scheduled report generation (§9.9) 🆕
- [ ] Celery Beat tasks for daily compliance summary, weekly PDF, monthly audit export
- [ ] Admin UI to configure report schedules and recipients
- [ ] Delivery via email or save to configured path

**Owner**: Backend + Frontend  
**Refs**: `backend/config/celery_app.py`, `backend/apps/deployments/tasks.py`

### 16) Agent update distribution (§12.8) 🆕
- [ ] Backend: upload new agent package, trigger `update_agent` command via WebSocket
- [ ] Agent: download, verify checksum, self-update, restart
- [ ] Admin UI: agent version management page

**Owner**: Backend + Realtime + Agent  
**Refs**: `agent/agent.py`, `realtime/routes/agents.py`

---

## 🟢 Low priority (polish)

### 17) Heartbeat status lag reduction (§12.7)
- [ ] Measure end-to-end heartbeat latency and stale-device marking lag
- [ ] Reduce observed offline drift in UI (target: status changes within expected 5-minute window)
- [ ] Add monitoring metric/logs for heartbeat processing delay

**Owner**: Agent + Realtime + Backend  
**Refs**: `agent/agent.py`, `realtime/routes/agents.py`, `backend/apps/inventory/tasks.py`

### 18) Production release verification refresh
- [ ] Re-run full final verification with current feature set and docs
- [ ] Update release notes with resolved gaps and known limitations
- [ ] Mark tracker statuses only after tested acceptance criteria are met

**Owner**: QA + Release  
**Refs**: `tasks/phase-10-deployment/task-10.4-final-verification.md`, `RELEASE_NOTES.md`

---

## Release gate

- **Total gaps**: 23
- **🔴 Blockers**: 3 (items 1–3)
- **🟠 High priority**: 4 (items 4–7)
- **🟡 Medium priority**: 9 (items 8–16)
- **🟢 Low priority**: 2 (items 17–18)
- **Go/No-Go**: **NO-GO** until all 🔴 blockers and 🟠 high-priority items are resolved.

