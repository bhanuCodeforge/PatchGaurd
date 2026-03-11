# PatchGuard — Device Details Redesign

> **Version**: 2.0  
> **Date**: 2026-04-11  
> **Scope**: Complete redesign of the device details experience for enterprise-grade patch management at 10k–100k device scale.

---

## Table of Contents

1. [Gap Analysis of Current Implementation](#1-gap-analysis)
2. [New Information Architecture](#2-information-architecture)
3. [Tab & Section Layout](#3-tab--section-layout)
4. [Data Model Improvements](#4-data-model-improvements)
5. [WebSocket Event Design](#5-websocket-event-design)
6. [Fast Lane / Slow Lane Execution Design](#6-fast-lane--slow-lane-execution-design)
7. [Performance Optimizations](#7-performance-optimizations)
8. [Security & Audit](#8-security--audit)
9. [Component Map](#9-component-map)
10. [Backend API Changes](#10-backend-api-changes)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Gap Analysis

### Current State

The existing device-full-detail component has **7 tabs** (Overview, Patches, System Info, Deployments, Activity Log, Security & Inventory, Settings) with ~480 lines of TypeScript and ~1200 lines of HTML. It works but has significant gaps:

| Area | Gap | Impact |
|------|-----|--------|
| **Information Architecture** | Overview duplicates patch counts shown in Patches tab. System Info duplicates metadata shown in Overview gauges. | Cognitive load, wasted screen space |
| **Fast Lane / Slow Lane** | No UI visibility into which lane is active, configurable, or being used per job. Scheduler intervals are buried in agent config. | Operators can't control urgency of execution |
| **Agent Health** | Only status dot (online/offline) and last_seen. No heartbeat timeline, no task queue visibility, no execution history. | Can't diagnose agent issues |
| **Patch Lifecycle** | Missing "pending reboot" state. No CVE drill-down, no patch timeline, no deployment association per patch. | Incomplete patch lifecycle tracking |
| **Execution Control** | Scan and Reboot are hero-bar icons. No "Install this patch now" per-patch action. No bulk install from device detail. | Operators must navigate to Deployments to act |
| **Real-time** | WebSocket updates metrics but doesn't live-update patch status, deployment progress, or activity log. | Stale data between refreshes |
| **Observability** | No structured timeline. Activity log is a flat table with no filtering, no expandable error details, no retry visibility. | Can't debug patch failures efficiently |
| **Performance** | Loads all patches (page_size=500) upfront. Slow-lane data loaded per section but not cached. No virtual scrolling on large lists. | Sluggish at 200+ patches per device |
| **Settings** | Only log_level and heartbeat_interval. No fast/slow lane config, no bandwidth control, no retry strategy. | Operators can't tune agent behavior |
| **Security** | API key shown nowhere (except on create). No rotation UI, no key age indicator, no audit trail of config changes. | Blind spot for security teams |

### What's Working Well

- Hero card design with quick actions is strong
- Severity/state badges are clear and consistent
- Slow-lane section picker (OS-specific chips) is a good pattern
- WebSocket integration for real-time metrics (fast lane) works
- Compliance bar in hero card is useful at a glance

---

## 2. Information Architecture

### Design Principles

1. **No duplication** — each data point appears in exactly one canonical location
2. **Progressive disclosure** — summary → detail → raw data
3. **Action proximity** — actions are next to the context they affect
4. **Lane-aware** — every execution-related UI element shows which lane (fast/slow) it uses
5. **Real-time first** — prefer WebSocket push over polling
6. **Lazy everything** — tabs load data only when activated; lists paginate and virtualize

### New Tab Structure (8 tabs)

```
┌─────────────────────────────────────────────────────────────────┐
│  [Hero Card]  hostname · IP · status · compliance · quick actions│
│  Tags: [production] [web-server]  Groups: [US-East Servers]     │
├──────┬──────────┬────────┬───────────┬──────────┬───────────────┤
│ Over │ Patches  │ Deploy │ Exec &    │ Invent-  │ Agent &       │
│ view │ & Comp-  │ ments  │ Timeline  │ ory      │ Settings      │
│      │ liance   │        │           │          │               │
└──────┴──────────┴────────┴───────────┴──────────┴───────────────┘
```

| # | Tab | Purpose | Data Sources |
|---|-----|---------|-------------|
| 1 | **Overview** | At-a-glance health, performance, and alert summary. No tables. | Fast-lane WS, device metadata |
| 2 | **Patches & Compliance** | Full patch lifecycle: available, installed, failed, pending-reboot. CVE details. Compliance gauge. | DevicePatchStatus API (paginated) |
| 3 | **Deployments** | Deployment history, per-deployment status, drill into waves. | DeploymentTarget API |
| 4 | **Execution & Timeline** | Structured event timeline (patch installs, scans, reboots, failures). Filterable. Expandable errors. | DeploymentEvent + Activity API + WS |
| 5 | **Inventory** | OS-specific slow-lane data: security, services, apps, drivers, etc. | Slow-lane API (on-demand per section) |
| 6 | **Agent & Settings** | Agent health, lane configuration, config push, API key management, danger zone. | Device metadata + WS + config API |

### Removed / Merged

- **System Info tab** → Hardware specs merged into Overview (spec grid). Network/storage details merged into Inventory.
- **Activity Log tab** → Merged into "Execution & Timeline" with richer structure.
- **Settings tab** → Expanded into "Agent & Settings" with lane config and security controls.

---

## 3. Tab & Section Layout

### 3.1 — Overview Tab

```
┌─────────────────────────────────────────────────────────────┐
│ ALERT BANNER (conditional)                                   │
│ ⚠ 3 critical patches pending · 1 failed deployment · reboot │
│   required                                                   │
├─────────────┬──────────────┬──────────────┬─────────────────┤
│ Patch       │  Compliance  │  Agent       │  Last           │
│ Summary     │  Rate        │  Status      │  Deployment     │
│ 12 pending  │  87.3%       │  ● Online    │  2h ago ✓       │
│  3 failed   │  ████████░░  │  HB: 4s ago  │  rolling/wave-2 │
├─────────────┴──────────────┴──────────────┴─────────────────┤
│ PERFORMANCE GAUGES (fast-lane, real-time)                    │
│ CPU [████████░░] 78%  RAM [██████░░░░] 62%  Disk [███░░] 31%│
├──────────────────────┬──────────────────────────────────────┤
│ LIVE I/O METRICS     │  SYSTEM SPECS (read-only)            │
│ Disk: ↑ 12 MB/s      │  OS: Windows Server 2022            │
│       ↓ 3.2 MB/s     │  CPU: 8 cores (Intel Xeon E5)       │
│ Net:  ↑ 45 KB/s      │  RAM: 32 GB                         │
│       ↓ 120 KB/s     │  Serial: DXYZ-1234                  │
│ Procs: 312            │  Agent: v1.4.2                      │
├──────────────────────┴──────────────────────────────────────┤
│ RECENT CRITICAL EVENTS (last 5, expandable)                  │
│ 🔴 10:32 — Patch KB5034441 FAILED (exit code 1603)          │
│ 🟢 10:30 — Patch KB5034440 installed                        │
│ 🟡 10:28 — Deployment "April Security" started              │
│ [View all in Timeline →]                                     │
└─────────────────────────────────────────────────────────────┘
```

**Key changes from current:**
- Added **alert banner** — highlights actionable items (critical patches, failures, reboot needed)
- Added **agent status card** with heartbeat recency
- Added **last deployment card** with quick status
- Moved system specs from a separate tab into a compact read-only grid
- Added **recent critical events** feed (not full activity log — just last 5 critical/warning events)
- Removed "Recently Updated Patches" table (it's in Patches tab now, and the critical events feed replaces it)

### 3.2 — Patches & Compliance Tab

```
┌─────────────────────────────────────────────────────────────┐
│ COMPLIANCE GAUGE                                             │
│ ████████████████████░░░░ 87.3%  (target: 95%)              │
│ 142 installed · 18 missing · 3 failed · 2 pending reboot   │
├──────┬───────────┬────────┬─────────────┬───────────────────┤
│ All  │ Available │ Failed │ Pend.Reboot │ Installed │ Recent│
│ (165)│   (18)    │  (3)   │    (2)      │  (142)    │       │
├──────┴───────────┴────────┴─────────────┴───────────────────┤
│ [Search patches...]  [Filter: severity ▾] [Sort: severity ▾]│
├─────────────────────────────────────────────────────────────┤
│  □  CVE-2026-1234  │ Windows Security Update │ CRITICAL │    │
│     KB5034441      │ CVSS 9.8 · Reboot: Yes  │          │    │
│     CVEs: CVE-2026-1234, CVE-2026-1235       │          │    │
│     [Install Now (Fast Lane)] [Schedule (Slow Lane)]    │    │
│                                                          │    │
│  □  CVE-2026-5678  │ .NET Runtime Update     │ HIGH     │    │
│     KB5034442      │ CVSS 7.5 · Reboot: No   │          │    │
│     [Install Now (Fast Lane)] [Schedule (Slow Lane)]    │    │
├─────────────────────────────────────────────────────────────┤
│ BULK ACTIONS: [Install Selected (Fast)] [Schedule (Slow)]   │
│               [Approve Selected]                             │
└─────────────────────────────────────────────────────────────┘
```

**Key changes:**
- Added **compliance gauge with target line** at top
- Added **"Pending Reboot"** sub-tab (new state)
- Added **per-patch actions**: "Install Now (Fast Lane)" and "Schedule (Slow Lane)"
- Added **search + filter + sort** controls
- Added **bulk actions** for selected patches (install, schedule, approve)
- Each patch row is **expandable** to show CVE details, affected components, and installation history

### 3.3 — Deployments Tab

```
┌─────────────────────────────────────────────────────────────┐
│ DEPLOYMENT HISTORY                                           │
├─────────────────────────────────────────────────────────────┤
│ ● April Security Rollout       │ COMPLETED │ 2h ago        │
│   Strategy: rolling (wave 3/3) │ 48/50 OK  │ 2 failed      │
│   [View Details] [View in Live Monitor]                      │
│                                                              │
│ ● March Cumulative Update      │ COMPLETED │ 12d ago       │
│   Strategy: immediate          │ 50/50 OK  │ 0 failed      │
│   [View Details]                                             │
│                                                              │
│ ● Emergency Zero-Day KB999     │ ROLLED BACK │ 15d ago     │
│   Strategy: canary             │ 5/50 OK   │ rollback at 10%│
│   ⚠ Rolled back: exit code 1603 on canary targets           │
│   [View Details] [View Rollback Log]                         │
└─────────────────────────────────────────────────────────────┘
```

**Key changes:**
- Added **strategy and wave progress** per deployment
- Added **failure count and rollback** visibility
- Added **drill-down links** to deployment detail and live monitor
- Cards instead of flat table rows — more scannable at a glance

### 3.4 — Execution & Timeline Tab

```
┌─────────────────────────────────────────────────────────────┐
│ FILTERS: [All] [Patches] [Deployments] [Agent] [Errors]    │
│ TIME:    [Last 24h ▾]  [Search events...]                   │
├─────────────────────────────────────────────────────────────┤
│ ─── Today ──────────────────────────────────────────────── │
│ 🔴 10:32  PATCH FAILED    KB5034441 — exit code 1603       │
│           ▸ Retry 2/3 · Fast Lane · Deployment: April Sec   │
│           ▸ stderr: "Error 0x80070005: Access denied"       │
│           ▸ [Retry Now] [View Deployment] [Copy Error]      │
│                                                              │
│ 🟢 10:30  PATCH INSTALLED  KB5034440                        │
│           ▸ Fast Lane · 12.3s install time                  │
│                                                              │
│ 🟡 10:28  DEPLOYMENT START "April Security Rollout"         │
│           ▸ Wave 3 · 50 devices · Rolling strategy          │
│                                                              │
│ 🔵 10:15  SCAN COMPLETE   18 missing patches discovered     │
│           ▸ Triggered by: admin@company.com                 │
│                                                              │
│ ⚪ 10:00  HEARTBEAT       CPU=45% RAM=62% Disk=31%         │
│           ▸ Agent v1.4.2 · Fast lane: 5s · Slow lane: 15m  │
│                                                              │
│ ─── Yesterday ──────────────────────────────────────────── │
│ 🟢 18:45  CONFIG CHANGE   heartbeat_interval: 60→30        │
│           ▸ Changed by: admin@company.com                   │
│ ...                                                          │
├─────────────────────────────────────────────────────────────┤
│ [Load more ▾]  (virtual-scrolled, 50 items per page)        │
└─────────────────────────────────────────────────────────────┘
```

**Key changes from current Activity Log:**
- **Structured timeline** with color-coded event types instead of flat table
- **Expandable rows** with full error details, retry info, and associated deployment
- **Filterable** by category (patches, deployments, agent, errors) and time range
- **Actionable** — retry failed patches inline, link to deployments
- **Virtual scrolled** with lazy loading (50 items per batch)
- **Real-time** — new events appear at the top via WebSocket push

### 3.5 — Inventory Tab

Same OS-specific chip picker as current, but reorganized into **categories**:

```
┌─────────────────────────────────────────────────────────────┐
│ Last collected: 12 min ago · Collection time: 8.2s          │
│ [↻ Refresh Inventory]                                        │
├─────────────────────────────────────────────────────────────┤
│ SECURITY                                                     │
│ [🛡 Defender] [🔥 Firewall] [🔒 Security Config]            │
│                                                              │
│ SOFTWARE                                                     │
│ [📦 Apps (342)] [🏪 Store Apps] [📦 Packages] [🧩 Features] │
│                                                              │
│ SYSTEM                                                       │
│ [⚙ Services (186)] [💻 Drivers] [📋 Tasks] [🚀 Startup]    │
│                                                              │
│ HARDWARE & NETWORK                                           │
│ [💾 Disk Health] [🌐 Network] [👥 Users]                    │
│                                                              │
│ LOGS                                                         │
│ [🔴 Event Errors] [📜 Update History] [⚠ Missing Updates]  │
├─────────────────────────────────────────────────────────────┤
│ [Selected section content with table/grid display]           │
│ (unchanged from current implementation — it works well)      │
└─────────────────────────────────────────────────────────────┘
```

**Key change:** Chips grouped by category instead of flat list. Easier to scan when there are 16+ sections.

### 3.6 — Agent & Settings Tab

```
┌─────────────────────────────────────────────────────────────┐
│ AGENT HEALTH                                                 │
│ ┌──────────────┬──────────────┬──────────────┐              │
│ │ Status       │ Heartbeat    │ Agent Version│              │
│ │ ● Online     │ 4s ago       │ v1.4.2       │              │
│ │              │ Interval: 5s │ Latest: 1.4.2│              │
│ └──────────────┴──────────────┴──────────────┘              │
│                                                              │
│ LANE CONFIGURATION                                           │
│ ┌─────────────────────────┬─────────────────────────┐       │
│ │ ⚡ FAST LANE            │ 🐢 SLOW LANE            │       │
│ │ Interval: [5s    ]      │ Interval: [900s   ]     │       │
│ │ Concurrency: [2  ]      │ Concurrency: [1   ]     │       │
│ │ Max bandwidth: [—  ]    │ Max bandwidth: [—  ]    │       │
│ │ Retry on fail: [3 ]     │ Retry on fail: [3  ]    │       │
│ │ Retry delay: [30s ]     │ Retry delay: [60s  ]    │       │
│ └─────────────────────────┴─────────────────────────┘       │
│ [Push Config to Agent]                                       │
│                                                              │
│ DEVICE PROPERTIES                                            │
│ Hostname: [prod-web-01     ]                                │
│ Description: [Primary web server ]                          │
│ [Save Changes]                                               │
│                                                              │
│ SECURITY                                                     │
│ API Key Age: 42 days (next rotation in 48 days)             │
│ [Rotate API Key Now]  [View Key]                            │
│ Key created: 2026-02-28 · Last rotated: 2026-02-28         │
│                                                              │
│ ⚠ DANGER ZONE                                               │
│ [Delete Device]  [Decommission Device]                      │
└─────────────────────────────────────────────────────────────┘
```

**Key changes:**
- Added **full lane configuration** (fast and slow) with all tuning parameters
- Added **agent health card** with heartbeat recency and version comparison
- Added **API key security section** with age indicator, rotation schedule
- Added **Decommission** action (separate from delete — marks as decommissioned without data loss)
- Config push clearly labeled as "Push Config to Agent" with real-time delivery indicator

---

## 4. Data Model Improvements

### 4.1 — New `pending_reboot` State

```python
# patches/models.py — DevicePatchStatus
class State(models.TextChoices):
    MISSING = "missing", "Missing"
    PENDING = "pending", "Pending"
    INSTALLED = "installed", "Installed"
    FAILED = "failed", "Failed"
    PENDING_REBOOT = "pending_reboot", "Pending Reboot"  # NEW
```

### 4.2 — Lane Tracking on DevicePatchStatus

```python
# patches/models.py — DevicePatchStatus (add fields)
execution_lane = models.CharField(
    max_length=10, choices=[("fast", "Fast"), ("slow", "Slow")],
    blank=True, default=""
)
execution_duration_ms = models.IntegerField(null=True, blank=True)
```

### 4.3 — Agent Lane Config on Device

```python
# inventory/models.py — Device (add to metadata or new JSONField)
lane_config = models.JSONField(default=dict, blank=True, help_text="Lane scheduler config")
# Schema:
# {
#   "fast_lane": {"interval": 5, "concurrency": 2, "max_bandwidth_mbps": null, "retry_count": 3, "retry_delay_sec": 30},
#   "slow_lane": {"interval": 900, "concurrency": 1, "max_bandwidth_mbps": null, "retry_count": 3, "retry_delay_sec": 60}
# }
```

### 4.4 — Timeline Event Model

Extend the existing `DeploymentEvent` model to support device-level events (not just deployment events):

```python
# inventory/models.py — DeviceEvent (new)
class DeviceEvent(models.Model):
    class EventType(models.TextChoices):
        HEARTBEAT = "heartbeat"
        SCAN_START = "scan_start"
        SCAN_COMPLETE = "scan_complete"
        PATCH_INSTALL_START = "patch_install_start"
        PATCH_INSTALL_SUCCESS = "patch_install_success"
        PATCH_INSTALL_FAILED = "patch_install_failed"
        DEPLOYMENT_START = "deployment_start"
        DEPLOYMENT_COMPLETE = "deployment_complete"
        DEPLOYMENT_FAILED = "deployment_failed"
        REBOOT_REQUESTED = "reboot_requested"
        REBOOT_COMPLETE = "reboot_complete"
        CONFIG_CHANGE = "config_change"
        KEY_ROTATED = "key_rotated"
        AGENT_UPDATE = "agent_update"
        SLOW_LANE_COMPLETE = "slow_lane_complete"
        ERROR = "error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices, db_index=True)
    severity = models.CharField(max_length=10, choices=[("info","Info"),("warning","Warning"),("error","Error"),("critical","Critical")], default="info")
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=50, default="agent")  # "agent", "system", "user:admin@co.com"
    deployment_id = models.UUIDField(null=True, blank=True, db_index=True)
    patch_id = models.UUIDField(null=True, blank=True)
    execution_lane = models.CharField(max_length=10, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "device_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "-created_at"]),
            models.Index(fields=["device", "event_type"]),
        ]
```

---

## 5. WebSocket Event Design

### Current Events (kept)

| Event | Direction | Payload |
|-------|-----------|---------|
| `agent_heartbeat` | Agent→Server→Dashboard | `{device_id, cpu, ram, disk, ...}` |
| `agent_metrics` | Agent→Server→Dashboard | Fast-lane metrics blob |
| `agent_slow_lane_data` | Agent→Server→Dashboard | Section inventory data |
| `status_change` | Server→Dashboard | `{device_id, status}` |
| `scan_results` | Agent→Server→Dashboard | `{device_id, patches[]}` |

### New Events

| Event | Direction | Payload | Purpose |
|-------|-----------|---------|---------|
| `patch_install_start` | Server→Dashboard | `{device_id, patch_id, vendor_id, lane}` | Live install tracking |
| `patch_install_result` | Server→Dashboard | `{device_id, patch_id, status, error, duration_ms, lane}` | Live result update |
| `deployment_wave_progress` | Server→Dashboard | `{deployment_id, device_id, wave, completed, total}` | Wave progress in device context |
| `device_timeline_event` | Server→Dashboard | `{device_id, event_type, severity, message, details}` | Live timeline feed |
| `lane_config_updated` | Server→Agent | `{fast_lane: {...}, slow_lane: {...}}` | Push lane config changes |
| `reboot_required` | Agent→Server→Dashboard | `{device_id, patch_ids[]}` | Trigger reboot-needed alert |
| `agent_task_queue` | Agent→Server→Dashboard | `{device_id, queue: [{task, status, lane}]}` | Agent execution queue state |

### Event Flow for Patch Install

```
1. Dashboard sends POST /devices/{id}/install_patch/
   → Backend publishes Redis command: EXECUTE_PATCH {patch_id, lane: "fast"}
   
2. Realtime server routes command to agent via WebSocket
   → Agent receives EXECUTE_PATCH

3. Agent emits WS: {event: "patch_install_start", device_id, patch_id, lane: "fast"}
   → Realtime broadcasts to dashboard subscribers
   
4. Agent completes install
   → Agent emits WS: {event: "patch_install_result", status: "success"|"failed", ...}
   → Realtime broadcasts + POSTs to /deployments/{id}/ingest_patch_result/
   
5. Dashboard receives event → updates patch row state in real-time
   → Timeline tab gets new event automatically
```

---

## 6. Fast Lane / Slow Lane Execution Design

### Conceptual Model

```
               ┌─────────────┐
               │   OPERATOR   │
               │  "Install    │
               │   this now"  │
               └──────┬───────┘
                      │
            ┌─────────┴──────────┐
            ▼                    ▼
    ⚡ FAST LANE           🐢 SLOW LANE
    ─────────────         ──────────────
    Immediate exec        Queued/scheduled
    No approval needed*   May need approval
    Single patch          Batch patches
    Zero-day response     Maintenance window
    High concurrency      Bandwidth limited
    ─────────────         ──────────────
    UI: orange button     UI: blue button
    "Install Now"         "Schedule"
```

### UI Integration Points

| Location | Fast Lane Action | Slow Lane Action |
|----------|-----------------|-----------------|
| Patch row (Patches tab) | "Install Now ⚡" button | "Schedule 🐢" button |
| Bulk actions bar | "Install Selected (Fast)" | "Schedule Selected (Slow)" |
| Overview alert banner | "Fix Critical Now ⚡" | — |
| Deployment detail | — | "Add to deployment" |

### Agent Config Schema (pushed via WebSocket)

```yaml
fast_lane:
  interval: 5              # metrics collection interval (sec)
  concurrency: 2           # max parallel patch installs
  max_bandwidth_mbps: null  # null = unlimited
  retry_count: 3           # retries on failure
  retry_delay_sec: 30      # delay between retries

slow_lane:
  interval: 900            # inventory collection interval (sec)
  concurrency: 1           # max parallel patch installs
  max_bandwidth_mbps: 50   # bandwidth cap for download
  retry_count: 3
  retry_delay_sec: 60
```

### Backend: New Endpoint

```python
# inventory/views.py — new action
@action(detail=True, methods=["post"], url_path="install_patch", permission_classes=[IsOperatorOrAbove])
def install_patch(self, request, pk=None):
    """
    Trigger per-patch install on a specific device.
    Body: { "patch_id": "uuid", "lane": "fast"|"slow" }
    """
    device = self.get_object()
    patch_id = request.data.get("patch_id")
    lane = request.data.get("lane", "fast")
    
    RedisPublisher.publish_agent_command(
        str(device.id), "EXECUTE_PATCH",
        {"patch_id": patch_id, "lane": lane, "initiated_by": request.user.username}
    )
    
    # Record timeline event
    DeviceEvent.objects.create(
        device=device, event_type=DeviceEvent.EventType.PATCH_INSTALL_START,
        message=f"Patch install triggered via {lane} lane",
        details={"patch_id": patch_id, "lane": lane},
        source=f"user:{request.user.username}",
        execution_lane=lane
    )
    
    return Response({"status": "install command sent", "lane": lane})
```

---

## 7. Performance Optimizations

### 7.1 — Patch Loading

**Current:** `page_size=500` (loads all patches upfront)  
**New:** Server-side pagination with `page_size=50`, client-side virtual scrolling

```typescript
// Load patches on-demand per sub-tab with pagination
loadPatches(state: string, page: number = 1) {
  this.deviceSvc.getDevicePatches(this.deviceId, {
    state: state,
    page: page,
    page_size: 50,
    ordering: '-patch__severity'
  }).subscribe(...)
}
```

### 7.2 — Tab Lazy Loading

Only load data when a tab is activated for the first time:

```typescript
private tabLoaded = new Set<string>();

onTabChange(tab: string) {
  if (this.tabLoaded.has(tab)) return;
  this.tabLoaded.add(tab);
  
  switch (tab) {
    case 'patches': this.loadPatchSummary(); break;
    case 'deployments': this.loadDeployments(); break;
    case 'timeline': this.loadTimeline(); break;
    case 'inventory': this.loadSlowLaneSummary(); break;
    case 'settings': this.loadLaneConfig(); break;
  }
}
```

### 7.3 — WebSocket Debouncing

```typescript
// Debounce fast-lane metrics to avoid excessive change detection
private metricsSubject = new BehaviorSubject<any>(null);
liveMetrics$ = this.metricsSubject.pipe(
  debounceTime(500),
  distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b))
);
```

### 7.4 — Virtual Scrolling for Large Lists

Use Angular CDK `VirtualScrollViewport` for:
- Installed apps (can be 300+)
- Slow-lane tables (services 186+, drivers 200+, processes 100+)
- Timeline events

### 7.5 — Inventory Section Caching

```typescript
private sectionCache = new Map<string, { data: any, ts: number }>();

loadSlowSection(section: string) {
  const cached = this.sectionCache.get(section);
  if (cached && Date.now() - cached.ts < 60_000) {
    this.slowSectionData.set(cached.data);
    return;
  }
  // ... fetch from server
}
```

### 7.6 — Backend: Select-Related Optimization

```python
# Ensure all patch queries use select_related to avoid N+1
DevicePatchStatus.objects.filter(device=device).select_related('patch').order_by(...)
```

---

## 8. Security & Audit

### API Key Management UI

- Show key age (days since creation/rotation)
- Show next auto-rotation date (90-day cycle)
- Warning indicator when key age > 80 days
- Rotate button with confirmation dialog
- View key button (in a secure dialog, copied to clipboard, auto-hidden after 30s)

### Audit Trail

All operator actions are logged to `DeviceEvent`:
- Config changes (who changed what, old→new values)
- Patch installs triggered (who, which patch, which lane)
- Reboots triggered (who)
- Key rotations (who, when)
- Device property edits (who, which fields)

### Sensitive Action Isolation

The Danger Zone section is enhanced:
- **Delete Device** — requires typing hostname to confirm (already implemented)
- **Decommission Device** — new action, soft-delete without data loss
- **Force Rotate Key** — requires admin role, warns about agent disconnection

---

## 9. Component Map

```
device-full-detail/
├── device-full-detail.component.ts          # Main container + tab routing
├── device-full-detail.component.html        # Template
├── device-full-detail.component.scss        # Styles
│
├── sections/
│   ├── overview-tab/
│   │   ├── overview-tab.component.ts        # Alert banner + stats + gauges + specs
│   │   └── overview-tab.component.html
│   │
│   ├── patches-tab/
│   │   ├── patches-tab.component.ts         # Patch lifecycle + compliance + bulk actions
│   │   ├── patch-row.component.ts           # Expandable patch row with actions
│   │   └── patches-tab.component.html
│   │
│   ├── deployments-tab/
│   │   ├── deployments-tab.component.ts     # Deployment history cards
│   │   └── deployments-tab.component.html
│   │
│   ├── timeline-tab/
│   │   ├── timeline-tab.component.ts        # Structured event timeline
│   │   ├── timeline-event.component.ts      # Single expandable event row
│   │   └── timeline-tab.component.html
│   │
│   ├── inventory-tab/
│   │   ├── inventory-tab.component.ts       # Categorized chip picker + section display
│   │   └── inventory-tab.component.html
│   │
│   └── agent-settings-tab/
│       ├── agent-settings-tab.component.ts  # Lane config + device props + security + danger zone
│       └── agent-settings-tab.component.html
│
└── shared/
    ├── alert-banner.component.ts            # Conditional critical alert strip
    ├── lane-badge.component.ts              # ⚡ Fast / 🐢 Slow badge
    └── compliance-gauge.component.ts        # Circular/bar gauge with target line
```

### Refactoring Notes

The current monolithic `device-full-detail.component.ts` (480 lines) and template (1200 lines) should be split into the above sub-components. Each tab section becomes its own component with:
- Its own signal-based state
- Its own data loading
- Its own WebSocket subscription filter

The parent component handles:
- Device loading
- Tab routing
- WebSocket connection setup (passes filtered observables to child components)

---

## 10. Backend API Changes

### New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/devices/{id}/install_patch/` | Trigger per-patch install on a device (fast/slow lane) |
| POST | `/devices/{id}/decommission/` | Soft-delete: mark as decommissioned |
| GET | `/devices/{id}/timeline/` | Paginated timeline events (filterable by type, severity, time range) |
| POST | `/devices/{id}/lane_config/` | Push lane configuration to agent |
| GET | `/devices/{id}/agent_health/` | Agent status, heartbeat stats, version, queue |
| GET | `/devices/{id}/alert_summary/` | Critical patches count, failures, reboot needed |

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `GET /devices/{id}/patches/` | Add `pending_reboot` state filter. Add `lane` field in response. |
| `GET /devices/{id}/activity/` | Deprecated in favor of `/devices/{id}/timeline/` |
| `POST /devices/{id}/agent_config/` | Accept full lane_config object alongside log_level/heartbeat_interval |

---

## 11. Implementation Roadmap

### Phase A — Data Model & Backend (3–5 days)

1. Add `pending_reboot` state to DevicePatchStatus
2. Add `execution_lane`, `execution_duration_ms` to DevicePatchStatus
3. Create `DeviceEvent` model + migration
4. Add `lane_config` field to Device
5. Implement new endpoints: `install_patch`, `timeline`, `lane_config`, `decommission`, `alert_summary`, `agent_health`
6. Add DeviceEvent creation in existing task flows (scan, deploy, heartbeat)

### Phase B — WebSocket Events (2–3 days)

7. Add new event types to realtime routes (patch_install_start/result, timeline_event, lane_config_updated, reboot_required, agent_task_queue)
8. Wire DeviceEvent creation triggers to also broadcast via WebSocket
9. Update agent to emit patch_install_start/result and reboot_required events

### Phase C — Frontend Restructure (5–7 days)

10. Split monolithic component into tab sub-components
11. Implement Overview tab with alert banner and agent status
12. Implement Patches tab with per-patch actions and bulk operations
13. Implement Timeline tab with filtering, expansion, and virtual scroll
14. Implement Agent & Settings tab with lane config and security section
15. Reorganize Inventory tab chip categories
16. Update Deployments tab with cards and drill-down

### Phase D — Performance & Polish (2–3 days)

17. Server-side pagination for patches (remove page_size=500)
18. Tab lazy loading
19. WebSocket debouncing with BehaviorSubject
20. Virtual scrolling for large inventories
21. Section caching for slow-lane data

---

## References

- Current implementation: `frontend/src/app/features/devices/device-full-detail/`
- Backend views: `backend/apps/inventory/views.py`
- Agent scheduler: `agent/collectors/scheduler.py`
- WebSocket manager: `realtime/ws_manager.py`
- Phase 11 gaps: `tasks/phase-11-critical-gaps.md`
