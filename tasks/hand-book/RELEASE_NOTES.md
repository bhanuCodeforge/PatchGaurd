# Release Notes — PatchGuard v1.0.0-rc.1

## Overview
This is the first Release Candidate for the PatchGuard Enterprise platform, focusing on production readiness, cross-platform agent support, and real-time orchestration.

## New Features
- **Centralized Inventory**: Automatic discovery and grouping of Windows, Linux, and macOS endpoints.
- **Real-Time Orchestration**: WebSocket-based command execution for scans and reboots.
- **Patch Lifecycle**: Approval workflows with severity-based compliance reporting.
- **Role-Based Access Control**: Granular permissions (Admin, Operator, Viewer).
- **Audit Logging**: Comprehensive tracking of all administrative actions.

## Production Hardening
- **Security**: NGINX SSL termination, HSTS/CSP headers, and secure cookie handling.
- **Operations**: Automated backup/restore scripts and deployment automation.
- **Monitoring**: Health check endpoints and built-in diagnostic commands.

## Known Issues
- Agent installation on macOS requires manual TCC permissions for full disk access.
- LDAP group synchronization is currently read-only.
