# PatchGuard 1.0 Parity Tasks

> **Last Updated**: 2026-04-09 — All items verified and marked complete.

## 1. Deployment Approval workflow (Sec 7.8) ✅
- [x] **Backend**: Implement logic in `DeploymentViewSet.execute` to require `IsAdmin` if `REQUIRE_APPROVAL` is enabled and deployment is not approved.
- [x] **Backend**: Ensure `DeploymentViewSet.approve` updates `status` to `SCHEDULED` and logs the approver.
- [x] **Frontend**: Update Deployment List to show "Approve" button for Admins on `DRAFT` deployments.
- [x] **Frontend**: Update Deployment Wizard to offer "Save as Draft" for Operators vs "Approve & Execute" for Admins.

## 2. Bulk Patch Operations (Sec 6.11) ✅
- [x] **Backend**: Extend `PatchViewSet` with `/bulk_reject` endpoint.
- [x] **Frontend**: Implement multi-select checkboxes in the Patch Catalog table.
- [x] **Frontend**: Add a floating action bar in Catalog for "Bulk Approve" and "Bulk Reject".

## 3. Real-time Heartbeat & Connectivity (Sec 12.7) ✅
- [x] **Agent**: Verify `heartbeat_interval` is strictly honored in the WebSocket loop.
- [x] **Realtime**: Optimize `ws_manager` to update `last_seen` immediately on heartbeat.
- [x] **Agent**: Delta-only heartbeat payloads (full every 10th beat), dynamic interval reload.

## 4. Advanced System Settings (Sec 13) ✅
- [x] **Backend**: SystemSetting model for SMTP, Webhooks, and Global Approval toggle.
- [x] **Frontend**: Build the "Advanced Settings" interface in `features/settings` (5 admin sections).
- [x] **Backend**: Maintenance Window Preset management endpoints.

## 5. Pre-flight Health Check Integration (Sec 7.6.2) ✅
- [x] **Backend**: Integrated `run_preflight_checks` result into the `execute_deployment` wave loop (60s polling, threshold checks).
- [x] **Backend**: Implement skip logic for unhealthy devices during a deployment wave (disk<10%, cpu>95%, mem>95%).

## 6. Global Search Enhancement (Sec 4.2) ✅
- [x] **Backend**: Update `DeviceFilter` to support a single `search` parameter that queries `hostname`, `ip_address`, and `tags` simultaneously.

## 7. Verification & Hardening ✅
- [x] **Backend**: Enrich `ComplianceReportView` with detailed SLA violation lists (breach table with severity, overdue duration).
- [x] **Backend**: Update `verify_platform` command to include TLS expiry and task health checks.

