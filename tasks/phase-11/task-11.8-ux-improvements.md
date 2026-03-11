
# Task 11.8 — Frontend UX Improvements

**Status**: ✅ Complete  
**Files**: `frontend/src/app/features/deployments/deployment-live/`

---

## Implementation

### CDK Virtual Scroll for Event Log

The deployment live monitor's event log previously rendered ALL events as `*ngFor` DOM nodes — causing significant performance degradation with 500+ events.

**Before**: `*ngFor` → N DOM nodes, browser freezes at scale  
**After**: `cdk-virtual-scroll-viewport [itemSize]="28"` → only ~12 visible rows rendered at any time

- **Max 5 000 events** kept in memory (signal array trimmed from top when full)
- **trackBy** function prevents unnecessary re-renders on WS message bursts
- **Autoscroll toggle**: ⏸ Pause / ▶ Follow button controls auto-pin to bottom

### Persistent Event History (Task 11.5 Integration)

On component init, fetches the backend `DeploymentEvent` audit log via:
```
GET /api/v1/deployments/{id}/events/
```
Populates the virtual scroll log before any new WS messages arrive — users see full history on page refresh.

### Deployment Service Update

Added `getDeploymentEvents(id: string)` method to `DeploymentService`.

### WS Message Routing

Updated `handleWsMessage` to look for `msg.payload.deployment_id` (new Streams envelope format from Task 11.3) as well as legacy `msg.deployment_id`.

### Dependencies Added

- `@angular/cdk@^21.0.0` installed via npm

---

## Completion Log

**Completed**: 2026-04-11  
**Angular build**: ✅ Clean (0 errors, 0 warnings on deployment-live)