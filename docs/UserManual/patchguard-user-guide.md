# PatchGuard — Complete User Guide

**Version**: 1.0  
**Last updated**: April 2026  
**Audience**: Administrators, Operators, Viewers  
**Deployment**: On-premises

---

## Table of Contents

1. [Getting Started](#1-getting-started)
   - 1.1 [System Requirements](#11-system-requirements)
   - 1.2 [Accessing PatchGuard](#12-accessing-patchguard)
   - 1.3 [First-Time Login](#13-first-time-login)
   - 1.4 [Password Policy](#14-password-policy)
   - 1.5 [LDAP / Active Directory Login](#15-ldap-active-directory-login)
   - 1.6 [Two-Factor Authentication (Future)](#16-two-factor-authentication)
   - 1.7 [Logging Out](#17-logging-out)
2. [User Interface Overview](#2-user-interface-overview)
   - 2.1 [Navigation Sidebar](#21-navigation-sidebar)
   - 2.2 [Top Bar](#22-top-bar)
   - 2.3 [Keyboard Shortcuts](#23-keyboard-shortcuts)
   - 2.4 [Dark Mode](#24-dark-mode)
   - 2.5 [Responsive Layout](#25-responsive-layout)
3. [Dashboard](#3-dashboard)
   - 3.1 [KPI Cards](#31-kpi-cards)
   - 3.2 [Compliance Breakdown Chart](#32-compliance-breakdown-chart)
   - 3.3 [Devices by OS Chart](#33-devices-by-os-chart)
   - 3.4 [Active Deployments Feed](#34-active-deployments-feed)
   - 3.5 [Critical Patches Pending Table](#35-critical-patches-pending-table)
   - 3.6 [Live Indicator & Auto-Refresh](#36-live-indicator-and-auto-refresh)
4. [Device Management](#4-device-management)
   - 4.1 [Device List View](#41-device-list-view)
   - 4.2 [Searching Devices](#42-searching-devices)
   - 4.3 [Filtering Devices](#43-filtering-devices)
   - 4.4 [Sorting & Pagination](#44-sorting-and-pagination)
   - 4.5 [Device Detail View](#45-device-detail-view)
   - 4.6 [Device Inventory Information](#46-device-inventory-information)
   - 4.7 [Device Patch Status Tab](#47-device-patch-status-tab)
   - 4.8 [Device Activity Log Tab](#48-device-activity-log-tab)
   - 4.9 [Device Deployment History Tab](#49-device-deployment-history-tab)
   - 4.10 [Resource Monitoring (CPU, RAM, Disk)](#410-resource-monitoring)
   - 4.11 [Adding a New Device](#411-adding-a-new-device)
   - 4.12 [Editing Device Details](#412-editing-device-details)
   - 4.13 [Bulk Operations](#413-bulk-operations)
   - 4.14 [Tagging Devices](#414-tagging-devices)
   - 4.15 [Decommissioning a Device](#415-decommissioning-a-device)
   - 4.16 [Exporting Device Data](#416-exporting-device-data)
5. [Device Groups](#5-device-groups)
   - 5.1 [Understanding Groups](#51-understanding-groups)
   - 5.2 [Static Groups](#52-static-groups)
   - 5.3 [Dynamic Groups](#53-dynamic-groups)
   - 5.4 [Creating a Group](#54-creating-a-group)
   - 5.5 [Editing a Group](#55-editing-a-group)
   - 5.6 [Nested Groups (Hierarchies)](#56-nested-groups)
   - 5.7 [Viewing Group Membership](#57-viewing-group-membership)
6. [Patch Catalog](#6-patch-catalog)
   - 6.1 [Patch Catalog Overview](#61-patch-catalog-overview)
   - 6.2 [Vendor Feed Sync](#62-vendor-feed-sync)
   - 6.3 [Searching & Filtering Patches](#63-searching-and-filtering-patches)
   - 6.4 [Patch Severity Levels](#64-patch-severity-levels)
   - 6.5 [Patch Status Lifecycle](#65-patch-status-lifecycle)
   - 6.6 [Viewing Patch Details](#66-viewing-patch-details)
   - 6.7 [CVE Information & KB Articles](#67-cve-information-and-kb-articles)
   - 6.8 [Approving a Patch](#68-approving-a-patch)
   - 6.9 [Rejecting a Patch](#69-rejecting-a-patch)
   - 6.10 [Superseded Patches](#610-superseded-patches)
   - 6.11 [Bulk Approve / Reject](#611-bulk-approve-reject)
   - 6.12 [Patch Applicability (OS Matching)](#612-patch-applicability)
7. [Deployments](#7-deployments)
   - 7.1 [Deployment Overview](#71-deployment-overview)
   - 7.2 [Deployment Status Lifecycle](#72-deployment-status-lifecycle)
   - 7.3 [Creating a Deployment (Wizard)](#73-creating-a-deployment)
     - 7.3.1 [Step 1: Select Patches](#731-step-1-select-patches)
     - 7.3.2 [Step 2: Select Targets](#732-step-2-select-targets)
     - 7.3.3 [Step 3: Configure Strategy](#733-step-3-configure-strategy)
     - 7.3.4 [Step 4: Review & Deploy](#734-step-4-review-and-deploy)
   - 7.4 [Rollout Strategies](#74-rollout-strategies)
     - 7.4.1 [Immediate Strategy](#741-immediate-strategy)
     - 7.4.2 [Canary Strategy](#742-canary-strategy)
     - 7.4.3 [Rolling Strategy](#743-rolling-strategy)
   - 7.5 [Strategy Parameters](#75-strategy-parameters)
     - 7.5.1 [Canary Size](#751-canary-size)
     - 7.5.2 [Wave Size](#752-wave-size)
     - 7.5.3 [Max Failure Rate](#753-max-failure-rate)
     - 7.5.4 [Wave Delay](#754-wave-delay)
     - 7.5.5 [Maintenance Window](#755-maintenance-window)
   - 7.6 [Safety Options](#76-safety-options)
     - 7.6.1 [Allow Reboot](#761-allow-reboot)
     - 7.6.2 [Pre-Flight Health Check](#762-pre-flight-health-check)
     - 7.6.3 [Auto-Rollback](#763-auto-rollback)
   - 7.7 [Scheduling a Deployment](#77-scheduling-a-deployment)
   - 7.8 [Approval Workflow](#78-approval-workflow)
8. [Live Deployment Monitor](#8-live-deployment-monitor)
   - 8.1 [Accessing the Monitor](#81-accessing-the-monitor)
   - 8.2 [Progress Bar & Statistics](#82-progress-bar-and-statistics)
   - 8.3 [Wave Progress Tracker](#83-wave-progress-tracker)
   - 8.4 [Device Heat Map](#84-device-heat-map)
   - 8.5 [Live Event Log](#85-live-event-log)
   - 8.6 [Pausing a Deployment](#86-pausing-a-deployment)
   - 8.7 [Resuming a Deployment](#87-resuming-a-deployment)
   - 8.8 [Cancelling a Deployment](#88-cancelling-a-deployment)
   - 8.9 [Failure Threshold Breaches](#89-failure-threshold-breaches)
   - 8.10 [Rollback Behavior](#810-rollback-behavior)
   - 8.11 [WebSocket Connection Status](#811-websocket-connection-status)
9. [Compliance & Reporting](#9-compliance-and-reporting)
   - 9.1 [Compliance Dashboard](#91-compliance-dashboard)
   - 9.2 [Compliance Rate Calculation](#92-compliance-rate-calculation)
   - 9.3 [Per-Device Compliance](#93-per-device-compliance)
   - 9.4 [Per-Group Compliance](#94-per-group-compliance)
   - 9.5 [Per-Patch Coverage](#95-per-patch-coverage)
   - 9.6 [Compliance Trend (30-Day)](#96-compliance-trend)
   - 9.7 [SLA Reporting](#97-sla-reporting)
   - 9.8 [Exporting Reports](#98-exporting-reports)
   - 9.9 [Scheduled Report Generation](#99-scheduled-report-generation)
10. [Audit Log](#10-audit-log)
    - 10.1 [What Gets Logged](#101-what-gets-logged)
    - 10.2 [Viewing the Audit Log](#102-viewing-the-audit-log)
    - 10.3 [Filtering Audit Entries](#103-filtering-audit-entries)
    - 10.4 [Audit Log Retention](#104-audit-log-retention)
    - 10.5 [Exporting Audit Data](#105-exporting-audit-data)
11. [User Management & RBAC](#11-user-management-and-rbac)
    - 11.1 [Role Definitions](#111-role-definitions)
    - 11.2 [Permission Matrix](#112-permission-matrix)
    - 11.3 [Creating a User](#113-creating-a-user)
    - 11.4 [Editing a User](#114-editing-a-user)
    - 11.5 [Deactivating a User](#115-deactivating-a-user)
    - 11.6 [Resetting a Password](#116-resetting-a-password)
    - 11.7 [Account Lockout Policy](#117-account-lockout-policy)
    - 11.8 [LDAP/AD Group Mapping](#118-ldap-ad-group-mapping)
    - 11.9 [API Keys for Agents](#119-api-keys-for-agents)
12. [Agent Management](#12-agent-management)
    - 12.1 [Agent Overview](#121-agent-overview)
    - 12.2 [Agent Installation (Linux)](#122-agent-installation-linux)
    - 12.3 [Agent Installation (Windows)](#123-agent-installation-windows)
    - 12.4 [Agent Installation (macOS)](#124-agent-installation-macos)
    - 12.5 [Agent Configuration File](#125-agent-configuration-file)
    - 12.6 [Agent Registration](#126-agent-registration)
    - 12.7 [Agent Heartbeat & Status](#127-agent-heartbeat-and-status)
    - 12.8 [Agent Updates](#128-agent-updates)
    - 12.9 [Agent Troubleshooting](#129-agent-troubleshooting)
13. [System Settings](#13-system-settings)
    - 13.1 [General Settings](#131-general-settings)
    - 13.2 [Vendor Feed Configuration](#132-vendor-feed-configuration)
    - 13.3 [Notification Settings](#133-notification-settings)
    - 13.4 [Email / Webhook Alerts](#134-email-webhook-alerts)
    - 13.5 [Maintenance Window Presets](#135-maintenance-window-presets)
    - 13.6 [Data Retention Policies](#136-data-retention-policies)
    - 13.7 [TLS Certificate Management](#137-tls-certificate-management)
    - 13.8 [Backup & Restore](#138-backup-and-restore)
    - 13.9 [System Health Check](#139-system-health-check)
14. [API Reference](#14-api-reference)
    - 14.1 [Authentication Endpoints](#141-authentication-endpoints)
    - 14.2 [Device Endpoints](#142-device-endpoints)
    - 14.3 [Patch Endpoints](#143-patch-endpoints)
    - 14.4 [Deployment Endpoints](#144-deployment-endpoints)
    - 14.5 [Report Endpoints](#145-report-endpoints)
    - 14.6 [Swagger UI Access](#146-swagger-ui-access)
    - 14.7 [Rate Limiting](#147-rate-limiting)
    - 14.8 [Error Codes](#148-error-codes)
15. [Troubleshooting](#15-troubleshooting)
    - 15.1 [Login Issues](#151-login-issues)
    - 15.2 [Agent Connectivity Problems](#152-agent-connectivity-problems)
    - 15.3 [WebSocket Connection Drops](#153-websocket-connection-drops)
    - 15.4 [Deployment Stuck in Progress](#154-deployment-stuck-in-progress)
    - 15.5 [Patch Installation Failures](#155-patch-installation-failures)
    - 15.6 [High Database Load](#156-high-database-load)
    - 15.7 [Redis Connection Errors](#157-redis-connection-errors)
    - 15.8 [Celery Worker Issues](#158-celery-worker-issues)
    - 15.9 [Certificate Expiration](#159-certificate-expiration)
    - 15.10 [Performance Degradation](#1510-performance-degradation)
16. [Glossary](#16-glossary)

---

## 1. Getting Started

### 1.1 System Requirements

**Browser requirements**: PatchGuard supports the latest two versions of Chrome, Firefox, Edge, and Safari. JavaScript must be enabled. WebSocket support is required for real-time features.

**Network requirements**: HTTPS access to your PatchGuard server (default port 443). WebSocket connections on the same port (wss://). No external internet access is required — the system is fully on-premises.

**Recommended screen resolution**: 1280×720 or higher. The interface is responsive and works on tablets, but is optimized for desktop use.

### 1.2 Accessing PatchGuard

Open your browser and navigate to the URL provided by your administrator, typically:

```
https://patchmgr.internal.corp
```

You will see the login screen. If you cannot reach the page, verify that DNS resolves the hostname and that your machine has network access to the PatchGuard server.

### 1.3 First-Time Login

When your account is created by an administrator, you receive a username and temporary password. On first login:

1. Enter your username and temporary password on the login screen.
2. You will be prompted to set a new password that meets the password policy (see 1.4).
3. After setting your new password, you are redirected to the dashboard.

If your organization uses LDAP/Active Directory, see section 1.5 instead.

**Session duration**: Your session lasts 30 minutes of inactivity. After 30 minutes without interaction, you will be logged out and need to re-authenticate. Active sessions refresh automatically — you won't be logged out while actively using the system.

### 1.4 Password Policy

Local accounts (non-LDAP) must follow these rules:

- Minimum 12 characters
- At least one uppercase letter, one lowercase letter, one digit, and one special character
- Cannot reuse the last 5 passwords
- Passwords must be changed every 90 days (configurable by admin)
- After 5 consecutive failed login attempts, the account is locked for 30 minutes

### 1.5 LDAP / Active Directory Login

If your organization has configured LDAP/AD integration, use your corporate credentials (domain username and password) to log in. PatchGuard maps AD group memberships to roles automatically:

| AD Group Name       | PatchGuard Role |
|---------------------|-----------------|
| PatchMgr-Admins     | Administrator   |
| PatchMgr-Operators  | Operator        |
| All other users     | Viewer          |

Your admin may have configured different group names. LDAP users do not need to set a separate PatchGuard password — authentication is handled entirely by your directory server.

### 1.6 Two-Factor Authentication

Two-factor authentication is planned for a future release. Currently, security is enforced through strong password policies, account lockout, and LDAP/AD integration.

### 1.7 Logging Out

Click your avatar (initials circle) in the top-right corner of the screen, then select "Log out". This invalidates your session token server-side. Always log out when using a shared workstation.

---

## 2. User Interface Overview

### 2.1 Navigation Sidebar

The left sidebar is your primary navigation. It is divided into sections:

**Overview**: Dashboard — the home screen with KPI summaries and live activity.

**Manage**: Devices (inventory and groups), Patches (catalog and approval), Deployments (create, monitor, and history).

**Reports**: Compliance reporting and audit log.

**System**: Settings (admin only) — vendor feeds, notifications, users, and system health.

The sidebar shows badge counts for items requiring attention: the red badge on "Patches" indicates how many patches are awaiting review. The device count next to "Devices" shows total registered devices.

### 2.2 Top Bar

The top bar shows the current page title, a live connection indicator (green dot when WebSocket is connected), the last sync timestamp, and your user avatar. Clicking the avatar opens a dropdown with "My profile", "Preferences", and "Log out".

### 2.3 Keyboard Shortcuts

| Shortcut       | Action                    |
|----------------|---------------------------|
| `G` then `D`   | Go to Dashboard           |
| `G` then `V`   | Go to Devices             |
| `G` then `P`   | Go to Patches             |
| `G` then `E`   | Go to Deployments         |
| `/`             | Focus search bar          |
| `Esc`           | Close modal / go back     |
| `?`             | Show keyboard shortcuts   |

### 2.4 Dark Mode

PatchGuard automatically follows your operating system's theme preference. If your OS is set to dark mode, PatchGuard renders in dark mode. There is no manual toggle — the interface adapts seamlessly.

### 2.5 Responsive Layout

On screens narrower than 900px, the sidebar collapses into a hamburger menu. The dashboard KPI cards stack to two columns, and detail views switch to single-column layout. The full feature set remains available on tablet and laptop screens.

---

## 3. Dashboard

The dashboard is the first screen you see after login. It provides a real-time overview of your fleet's patch compliance, active deployments, and critical issues.

### 3.1 KPI Cards

Four cards across the top row:

**Total devices**: The count of all registered devices excluding decommissioned ones. The sub-text shows net change this week (e.g., "+23 this week" means 23 new devices were registered).

**Online now**: Devices that have sent a heartbeat within the last 5 minutes. The percentage shows uptime rate (online / total). If this number drops suddenly, investigate network or agent issues.

**Compliance rate**: The percentage of applicable patches that are installed across all devices. Calculated as: `installed / (installed + pending + failed) × 100`. This is your headline security metric. Green means above 85%, amber means 60–85%, red means below 60%.

**Critical pending**: The count of critical-severity patches that are in "approved" status but not yet installed on all applicable devices. A red badge here means urgent action is needed. The sub-text shows how many are new since yesterday.

### 3.2 Compliance Breakdown Chart

A donut chart showing the distribution of patch states across all devices:

- **Green (Patched)**: Patches successfully installed.
- **Amber (Pending)**: Patches approved but not yet installed — either scheduled or awaiting a deployment.
- **Red (Failed)**: Patches where installation was attempted but failed. These require investigation.

The center of the donut shows the overall compliance percentage. Click the chart to navigate to the full compliance report.

### 3.3 Devices by OS Chart

A horizontal bar chart showing device counts by operating system family (Linux, Windows, macOS). Each bar shows the absolute count. This helps you understand your fleet composition and prioritize patching by platform.

### 3.4 Active Deployments Feed

A live list of the most recent deployments, showing:

- **Deployment name and description**
- **Progress bar** with percentage and current wave indicator
- **Status badge**: In progress (blue, animated), Canary (blue), Scheduled (amber), Complete (green), Failed (red)

Click any deployment to jump to its live monitor. The feed updates in real-time via WebSocket — you do not need to refresh the page.

### 3.5 Critical Patches Pending Table

A table of the most urgent unpatched vulnerabilities, sorted by severity then age. Columns: Patch ID (CVE or KB), Severity (with color dot), Affected device count, and Age (days since release). Red age values indicate patches older than 48 hours — these violate most SLA policies.

Click any row to open the patch detail view where you can approve and deploy.

### 3.6 Live Indicator and Auto-Refresh

The green "Live" dot in the top bar indicates an active WebSocket connection. When connected, all dashboard data updates in real-time without page refreshes:

- Device status changes appear instantly
- Deployment progress updates as agents report back
- New patches appear when vendor sync completes

If the dot turns gray, the WebSocket has disconnected. The system automatically attempts to reconnect with exponential backoff (1s, 2s, 4s, 8s, up to 30s). KPI card data also refreshes via REST API every 30 seconds as a fallback.

---

## 4. Device Management

### 4.1 Device List View

Navigate to **Devices** in the sidebar. The device list shows all registered devices in a table with columns: Hostname, IP Address, OS, Environment, Status, Compliance, Tags, and Last Seen.

Each row is clickable — clicking navigates to the device detail view (section 4.5).

The list uses cursor-based pagination for consistent performance regardless of fleet size. You can page through thousands of devices without slowdown.

### 4.2 Searching Devices

The search bar at the top accepts free-text queries that match against hostname, IP address, and tags simultaneously. Searching is instant (client-side for the current page, server-side for full results).

Examples:
- `web-prod` — finds all devices whose hostname contains "web-prod"
- `10.0.1` — finds all devices on the 10.0.1.x subnet
- `nginx` — finds all devices tagged with "nginx"

### 4.3 Filtering Devices

Chip-based filters below the search bar allow quick filtering by:

**Status**: Online, Offline, Maintenance. Click to toggle — click again to deselect. Multiple status filters use OR logic (e.g., selecting "Online" and "Maintenance" shows both).

**OS**: Linux, Windows, macOS.

**Environment**: Production, Staging, Development.

Filters combine with AND logic across categories. For example, selecting "Online" + "Linux" + "Production" shows only production Linux servers that are currently online.

Active filters are highlighted in blue. The device count in the page header updates to reflect filtered results.

### 4.4 Sorting and Pagination

Click any column header to sort by that column. Click again to reverse the sort direction. An arrow indicator shows the current sort column and direction.

Default sort: hostname ascending.

Pagination appears below the table showing "Showing 1–50 of 1,247 devices". Click page numbers or "Next" to navigate. You can change page size (25, 50, 100, 200) from a dropdown.

### 4.5 Device Detail View

Click any device row to navigate to its detail view. The detail view has three areas:

**Header card**: Shows device identity (hostname, IP, MAC address), OS icon, current status dot, and compliance bar. Below this is a metadata grid with 8 fields (OS version, architecture, environment, agent version, CPU cores, RAM, disk, uptime). Tags and group memberships are listed below the grid.

**Resource monitors**: Three horizontal bars showing live CPU usage, memory usage, and disk usage percentages. Bars change color based on utilization: green below 60%, amber 60–80%, red above 80%. These update via WebSocket heartbeats. Offline devices do not show resource monitors.

**Tabbed content area**: Three tabs described in sections 4.7–4.9.

Click "Back to devices" at the top to return to the list with your filters preserved.

### 4.6 Device Inventory Information

The metadata grid in the device header shows:

| Field          | Description                                     |
|----------------|-------------------------------------------------|
| OS             | Full OS name and version (e.g., Ubuntu 22.04 LTS) |
| Architecture   | CPU architecture (x86_64, arm64)                |
| Environment    | Production, Staging, or Development             |
| Agent version  | Version of the PatchGuard agent installed       |
| CPU            | Number of CPU cores                             |
| RAM            | Total RAM in GB                                 |
| Disk           | Total disk capacity in GB                       |
| Uptime         | Time since last reboot                          |

This data is reported by the agent during system info scans and updated every 6 hours or on agent restart.

### 4.7 Device Patch Status Tab

The default tab when viewing a device. Shows:

**Summary counters**: Three numbers at the top — Installed (green), Pending (amber), Failed (red).

**Patch table**: Lists every applicable patch for this device with columns: CVE/Patch ID, Title, Severity (badge), Status (badge), and Date (when installed, or "—" if pending).

Severity badges: Critical (red), High (amber), Medium (blue), Low (gray).

Status badges: Installed (green), Pending (amber), Failed (red).

Click any patch row to navigate to that patch's detail in the catalog.

### 4.8 Device Activity Log Tab

A timestamped chronological log of all events for this device:

- Heartbeats received
- Patch installations (success and failure)
- System scans completed
- Agent version updates
- Connection/disconnection events

Each entry has a colored dot: blue (info), green (success), red (error), amber (warning). The log shows the most recent 50 events. Older events are available in the full audit log (section 10).

### 4.9 Device Deployment History Tab

Lists all deployments that have targeted this device, showing: deployment name, date, patches included, status (completed/failed/skipped), and duration. Click any deployment to jump to its history view.

### 4.10 Resource Monitoring

The three resource bars (CPU, RAM, disk) provide at-a-glance server health. These are sourced from the agent's heartbeat messages sent every 60 seconds.

**Thresholds**:
- Green (healthy): 0–59%
- Amber (warning): 60–79%
- Red (critical): 80–100%

If a device consistently shows red resource utilization, consider whether patching (which may require additional resources) should be deferred or scheduled during off-peak hours.

### 4.11 Adding a New Device

Devices are typically added automatically when the PatchGuard agent is installed and registers with the server. However, administrators can pre-register devices manually:

1. Click the **"Add device"** button on the device list page.
2. Fill in: hostname, IP address, OS family, environment, and optionally tags.
3. The system generates a unique API key for the agent.
4. Copy the API key and use it to configure the agent on the target machine (see section 12.5).

### 4.12 Editing Device Details

Operators and administrators can edit device metadata:

1. Navigate to the device detail view.
2. Click the **"Edit"** button (pencil icon) in the header card.
3. Editable fields: hostname, environment, tags, group membership.
4. Non-editable fields (reported by agent): OS version, CPU, RAM, disk, agent version.
5. Click **"Save"** to commit changes.

### 4.13 Bulk Operations

Select multiple devices using checkboxes in the list view. A blue bulk action bar appears at the top showing the count of selected devices and available actions:

- **Tag**: Add or remove tags from all selected devices.
- **Assign group**: Add selected devices to a device group.
- **Scan now**: Trigger an immediate compliance scan on selected devices.
- **Decommission**: Mark selected devices as decommissioned (see 4.15).

Select all devices on the current page using the header checkbox. To select across pages, use "Select all matching" after applying filters.

### 4.14 Tagging Devices

Tags are free-form labels attached to devices for flexible categorization. Examples: `web`, `nginx`, `tier-1`, `pci-scope`, `legacy`.

**Adding tags**: Edit the device (section 4.12) or use bulk tagging (section 4.13). Tags are comma-separated. Tags must be lowercase, alphanumeric with hyphens allowed, max 50 characters each.

**Using tags**: Tags appear in the device list and can be searched/filtered. Dynamic device groups can use tag-based rules (e.g., "all devices tagged `pci-scope`").

### 4.15 Decommissioning a Device

Decommissioning a device removes it from active inventory without deleting its history:

1. Navigate to the device detail view or select it in the list.
2. Click **"Decommission"** (or use bulk action).
3. Confirm in the dialog. You can optionally add a reason.
4. The device status changes to "Decommissioned" and it no longer appears in normal views.
5. The agent API key is revoked — the agent can no longer connect.
6. Historical data (patches, deployments, audit entries) is retained.

To view decommissioned devices, use the filter "Show decommissioned" in the device list.

### 4.16 Exporting Device Data

Click the **"Export"** button on the device list page. Options:

- **CSV**: All visible columns for filtered/all devices.
- **JSON**: Full device records with nested patch status.
- **PDF**: Formatted device inventory report.

Exports respect current filters — if you're viewing only "Production Linux Online" devices, the export contains only those.

---

## 5. Device Groups

### 5.1 Understanding Groups

Groups organize devices for targeting in deployments. A device can belong to multiple groups. Groups are the primary mechanism for selecting which devices receive a patch deployment.

There are two types: static (manually managed membership) and dynamic (rule-based automatic membership).

### 5.2 Static Groups

Static groups have a fixed list of devices. You manually add and remove devices. Use static groups when you need precise control over membership, such as "Critical Infrastructure" or "Maintenance Window A".

### 5.3 Dynamic Groups

Dynamic groups define membership rules, and any device matching the rules is automatically included. Rules can match on: OS family, OS version, environment, tags, and combinations thereof.

Example rules:
- OS = Ubuntu 22.04 AND Environment = Production → captures all production Ubuntu 22.04 servers
- Tag contains "pci-scope" → captures all PCI-scoped devices regardless of OS

When new devices register and match a dynamic group's rules, they are automatically included.

### 5.4 Creating a Group

1. Navigate to **Devices → Groups** (tab or sidebar sub-item).
2. Click **"Create group"**.
3. Enter a name and description.
4. Choose **Static** or **Dynamic**.
5. For static: search and check devices to add.
6. For dynamic: build rules using the rule builder (dropdown selectors for field, operator, value).
7. Preview shows the matching device count.
8. Click **"Save"**.

### 5.5 Editing a Group

Click a group name to open its detail view. Click **"Edit"** to modify name, description, or membership/rules. Changes to dynamic group rules immediately recalculate membership.

### 5.6 Nested Groups

Groups can have parent-child relationships. A parent group's membership includes all devices from its children. This enables hierarchical targeting — deploying to "All Production" automatically includes "Production Linux", "Production Windows", and their children.

### 5.7 Viewing Group Membership

The group detail view shows a device list of current members with the same columns, search, and filter capabilities as the main device list. The device count badge shows total members.

---

## 6. Patch Catalog

### 6.1 Patch Catalog Overview

Navigate to **Patches** in the sidebar. The catalog is organized into tabs:

- **Awaiting review**: Patches imported from vendor feeds that need approval before deployment. Badge shows count.
- **Approved**: Patches approved and available for deployment.
- **All patches**: Complete catalog regardless of status.
- **Critical**: Only critical-severity patches. Badge shows count.

### 6.2 Vendor Feed Sync

PatchGuard automatically syncs with configured vendor feeds every 6 hours:

- **Canonical (Ubuntu)**: USN (Ubuntu Security Notices)
- **Red Hat**: RHSA (Red Hat Security Advisories)
- **Microsoft**: WSUS / Windows Update catalog

New patches appear in "Awaiting review". The last sync time is shown below the page title. Admins can trigger a manual sync from Settings → Vendor Feeds.

### 6.3 Searching and Filtering Patches

**Search**: Enter CVE IDs, KB numbers, package names, or free text in the search bar.

**Filter dropdowns**: Severity (Critical, High, Medium, Low), Vendor (Canonical, Microsoft, Red Hat), OS (Ubuntu 22.04, Windows Server 2022, RHEL 9, etc.).

Filters combine with AND logic. Search and filters work together.

### 6.4 Patch Severity Levels

| Severity | Color  | Meaning                                                    | SLA Target   |
|----------|--------|------------------------------------------------------------|--------------|
| Critical | Red    | Active exploitation or trivial remote exploit. CVSS 9.0+   | 72 hours     |
| High     | Amber  | Significant vulnerability, likely exploitable. CVSS 7.0–8.9| 7 days       |
| Medium   | Blue   | Moderate risk, requires specific conditions. CVSS 4.0–6.9  | 30 days      |
| Low      | Gray   | Minimal risk, theoretical or low-impact. CVSS 0.1–3.9     | 90 days      |

SLA targets are configurable by your administrator in Settings.

### 6.5 Patch Status Lifecycle

```
Imported → Reviewed → Approved → [Deployed]
                   ↘ Rejected
                        ↘ Superseded
```

- **Imported**: Newly synced from vendor feed. No action taken yet.
- **Reviewed**: An operator has examined the patch and marked it as reviewed, but not yet approved.
- **Approved**: Ready for deployment. Can now be selected in the deployment wizard.
- **Rejected**: Determined to be not applicable or undesirable. Rejected patches do not appear in deployment wizards.
- **Superseded**: A newer patch replaces this one. Automatically set when a superseding patch is imported.

### 6.6 Viewing Patch Details

Click any patch row to expand the detail panel below the table. The panel shows:

- **Header**: CVE ID, full title, severity badge with CVSS score, review status.
- **Metadata grid**: Vendor, package name, fix version, reboot requirement.
- **Description**: Full vulnerability description from the vendor advisory.
- **Action buttons**: Approve, Approve & Deploy Now, Reject, View KB Article.

### 6.7 CVE Information and KB Articles

Each patch links to its vendor advisory or KB article via the "View KB article" button. This opens the vendor's page in a new tab (e.g., Ubuntu USN page, Microsoft KB page). CVE IDs are listed and can be searched.

### 6.8 Approving a Patch

Operators and administrators can approve patches:

1. Navigate to the patch in the catalog (typically in the "Awaiting review" tab).
2. Click the **"Approve"** button in the table row or in the detail panel.
3. The patch status changes to "Approved" and it becomes available for deployment.

**Approve & Deploy Now**: A shortcut that approves the patch and immediately opens the deployment wizard with this patch pre-selected.

### 6.9 Rejecting a Patch

1. Click **"Reject"** on the patch.
2. A dialog asks for a reason (required). Example reasons: "Not applicable to our configuration", "Conflicts with internal package".
3. The patch moves to "Rejected" status with the reason recorded in the audit log.

Rejected patches can be re-approved later if circumstances change.

### 6.10 Superseded Patches

When a vendor releases a newer patch that replaces an older one, PatchGuard automatically marks the older patch as "Superseded" and links it to the newer version. Superseded patches cannot be deployed — only the latest version is available.

### 6.11 Bulk Approve / Reject

Select multiple patches using checkboxes, then use the bulk action bar to approve or reject all selected patches at once. Bulk rejection still requires a reason (one reason applied to all).

### 6.12 Patch Applicability

Each patch specifies which OS versions it applies to (e.g., "Ubuntu 22.04", "Ubuntu 24.04"). PatchGuard matches these against your device inventory to calculate the "Affected" count — how many devices need this patch.

A patch is considered "applicable" to a device if the device's OS version matches the patch's applicability list AND the patch is not already installed. The "Not Applicable" state is assigned to devices whose OS does not match.

---

## 7. Deployments

### 7.1 Deployment Overview

Navigate to **Deployments** in the sidebar. The deployment list shows all deployments with columns: Name, Status, Strategy, Patches, Target groups, Device count, Progress, Created date, and Created by.

Tabs: Active (in-progress and scheduled), Completed, All.

### 7.2 Deployment Status Lifecycle

```
Draft → Scheduled → In Progress → Completed
                               → Failed
         ↘ Cancelled
In Progress → Paused → In Progress (resumed)
                     → Cancelled
In Progress → Rolling Back → Rolled Back
```

| Status        | Meaning                                                        |
|---------------|----------------------------------------------------------------|
| Draft         | Created but not yet approved or scheduled                      |
| Scheduled     | Approved, waiting for maintenance window                       |
| In Progress   | Actively deploying to devices                                  |
| Paused        | Operator manually paused the deployment                        |
| Completed     | All waves finished, all devices processed                      |
| Failed        | Failure threshold exceeded or critical error                   |
| Cancelled     | Operator cancelled the deployment                              |
| Rolling Back  | Auto-rollback triggered, reverting changes                     |

### 7.3 Creating a Deployment

Click **"New deployment"** on the deployments page. This opens a 4-step wizard.

#### 7.3.1 Step 1: Select Patches

- Browse or search approved patches.
- Filter by severity, vendor, or OS.
- Check one or more patches to include.
- The sidebar summary updates with selected patch count and highest severity.
- You can only select patches with "Approved" status.

Click **"Continue to targets"** when ready.

#### 7.3.2 Step 2: Select Targets

- Browse all device groups with search and environment filters.
- Check groups to include. Each group shows its device count and description.
- The summary sidebar shows total selected groups and devices.
- A warning appears if targeting more than 500 devices, recommending canary strategy.
- "Select all shown" and "Deselect all" buttons for quick selection.

Click **"Continue to strategy"** when at least one group is selected.

#### 7.3.3 Step 3: Configure Strategy

Choose one of three strategies (see section 7.4 for details):

- **Immediate**: Single wave, all devices at once.
- **Canary**: Small test group first, then waves.
- **Rolling**: Even waves with delays between them.

Configure parameters with sliders (see section 7.5):
- Canary size (1–20%)
- Wave size (10–200 devices)
- Max failure rate (1–25%)

Configure scheduling:
- Wave delay between waves (5 min to 2 hours)
- Maintenance window (immediately, tonight, weekend, custom)

Configure safety options with toggles (see section 7.6):
- Allow reboot
- Pre-flight health check
- Auto-rollback on failure

The execution plan preview at the bottom shows calculated wave counts, estimated duration, and a visual wave strip.

Click **"Continue to review"**.

#### 7.3.4 Step 4: Review and Deploy

A comprehensive read-only summary of every choice made in steps 1–3:

- **Patches section**: CVE IDs, severity badges, vendor/package info, reboot indicators.
- **Targets section**: Group names with device counts, total device count.
- **Strategy section**: All parameter values in a two-column grid.
- **Safety options**: Checkmark list of enabled options.
- **Warning banner**: Summarizes impact (device count, reboot requirement).
- **Confirmation checkbox**: Required before the deploy button activates. States "I confirm I have reviewed this deployment and have change approval."

Click **"Schedule deployment"** to submit. A loading spinner shows during submission, then a success screen appears with a link to **"View deployment"** (opens the live monitor) or **"Back to dashboard"**.

### 7.4 Rollout Strategies

#### 7.4.1 Immediate Strategy

All target devices receive the patch simultaneously. No waves, no delays.

**Use when**: The patch is low-risk and you need maximum speed, or the fleet is small enough that simultaneous deployment is safe.

**Risk**: If the patch causes issues, all devices are affected at once with no opportunity to detect and halt.

#### 7.4.2 Canary Strategy

A small percentage of devices (the "canary") receive the patch first. If the canary wave succeeds (no failures exceed the threshold), the remaining devices are deployed in waves.

**Use when**: Deploying to production for the first time, critical patches with potential side effects, or large fleets where you want early warning.

**Configuration**:
- **Canary size**: Percentage of total devices (default 5%). The canary is drawn from across all target groups proportionally.
- **Wave size**: After canary succeeds, remaining devices deploy in waves of this size.
- **Canary validation**: The system waits for all canary devices to report success/failure before proceeding. If canary failure rate exceeds the max threshold, the deployment halts.

#### 7.4.3 Rolling Strategy

Devices deploy in sequential waves of equal size (no separate canary phase). Each wave must complete before the next begins, with a configurable delay between waves.

**Use when**: Steady, predictable deployments where you want per-wave verification but don't need a dedicated canary phase.

**Configuration**:
- **Wave size**: Devices per wave (default 50).
- **Wave delay**: Time between wave completion and next wave start (default 15 minutes).
- After each wave, the system checks the cumulative failure rate. If exceeded, deployment halts.

### 7.5 Strategy Parameters

#### 7.5.1 Canary Size

Slider: 1% to 20% of total target devices (default 5%).

A canary of 5% on 1,000 devices = 50 canary devices. These devices are selected from across all target groups to ensure representative coverage. If the canary succeeds, you have high confidence the remaining 950 will too.

Larger canary = more confidence but slower start. Smaller canary = faster but less representative.

#### 7.5.2 Wave Size

Slider: 10 to 200 devices per wave (default 50).

Controls how many devices receive the patch in each wave after the canary. Smaller waves = more granular control but longer total deployment time. Larger waves = faster but higher blast radius per wave.

#### 7.5.3 Max Failure Rate

Slider: 1% to 25% of total devices (default 5%).

If the cumulative failure rate exceeds this threshold at any point during the deployment, the system automatically halts the deployment. Remaining queued devices are not processed.

Example: 5% threshold on 1,000 devices = halt if more than 50 devices fail.

If auto-rollback is enabled, a halt also triggers rollback on failed devices.

#### 7.5.4 Wave Delay

Dropdown: 5 minutes, 15 minutes, 30 minutes, 1 hour, 2 hours (default 15 minutes).

The wait time between one wave completing and the next wave starting. This gives operators time to monitor for issues that appear after installation (e.g., service degradation that isn't captured by the agent's success/failure report).

#### 7.5.5 Maintenance Window

Dropdown options:
- **None — deploy immediately**: Starts as soon as you click deploy.
- **Tonight 02:00–06:00 UTC**: Waits until the next 02:00 UTC to begin.
- **Weekend window (Sat 00:00–06:00)**: Waits until the next Saturday.
- **Custom**: Opens a date/time picker.

If a maintenance window is selected, the deployment enters "Scheduled" status and begins automatically when the window opens. If the deployment cannot complete within the window, it pauses at the end of the window and resumes at the next window.

### 7.6 Safety Options

#### 7.6.1 Allow Reboot

Toggle (default: On if any selected patch requires reboot).

When enabled, devices that require a reboot after patch installation will be rebooted automatically. The agent schedules the reboot with a 60-second warning to connected users.

When disabled, patches are installed but the reboot is deferred. The device is flagged as "Reboot pending" in the device list.

#### 7.6.2 Pre-Flight Health Check

Toggle (default: On).

Before each wave begins, the system verifies that target devices are online and healthy (agent connected, disk space above 10%, no existing patch installation in progress). Devices that fail the pre-flight check are skipped for this wave and retried in a subsequent wave.

#### 7.6.3 Auto-Rollback

Toggle (default: On).

When the failure threshold is breached and the deployment halts, auto-rollback automatically reverts the patch on devices that reported failure. This requires the agent to support rollback for the specific patch type (package downgrade on Linux, uninstall on Windows).

Rollback is best-effort — some patches (particularly kernel updates that have been rebooted into) cannot be rolled back.

### 7.7 Scheduling a Deployment

Select a maintenance window in Step 3 of the wizard. The deployment is created with "Scheduled" status and a `scheduled_at` timestamp. The system's Celery Beat scheduler checks every minute for deployments whose scheduled time has arrived, and automatically starts execution.

You can also create a deployment as "Draft" (by not clicking deploy in step 4 — instead clicking "Save as draft") and have an administrator approve it later (see section 7.8).

### 7.8 Approval Workflow

For organizations requiring change management:

1. An operator creates a deployment and saves it as **Draft**.
2. An administrator reviews the deployment details.
3. The administrator clicks **"Approve"** on the deployment.
4. The deployment status changes to **Scheduled** (with the configured maintenance window) or **In Progress** (if set to deploy immediately).

Only administrators can approve deployments. Operators can create and configure them but cannot execute without approval if the "Require approval" setting is enabled in System Settings.

---

## 8. Live Deployment Monitor

### 8.1 Accessing the Monitor

Navigate to an in-progress deployment via:
- The **"View deployment"** button after creating a deployment
- Clicking an active deployment in the dashboard feed
- The deployments list, clicking any in-progress deployment

### 8.2 Progress Bar and Statistics

The top section shows:

**Overall progress bar**: A tri-color horizontal bar filling left to right.
- Green = completed devices
- Blue (animated pulse) = currently installing
- Red = failed devices
- Gray (remaining) = queued

**Percentage**: Large number showing `completed / total × 100`.

**Six stat cards**: Total, Completed (green), In Progress (blue), Failed (red), Queued, Failure Rate (turns red if approaching threshold).

All numbers update in real-time via WebSocket.

### 8.3 Wave Progress Tracker

Left panel showing each wave as a row:

- **Wave label**: "Canary", "Wave 1", "Wave 2", etc.
- **Progress bar**: Fills as devices in that wave complete.
- **Count**: "346/350" showing completed+failed / total.
- **Failure indicator**: Red text showing failure count if > 0.

Wave backgrounds: Green = complete, Blue = active, Gray = queued (dimmed).

The tracker scrolls if there are many waves, with the active wave always visible.

### 8.4 Device Heat Map

Right panel showing every device as a small colored square:

- **Green**: Patched successfully
- **Blue (blinking)**: Currently installing
- **Red**: Failed
- **Gray**: Queued

Hover over any square to see the device hostname in a tooltip. The grid provides an instant visual sense of deployment progress — you can literally see the "green wave" sweeping across your fleet.

### 8.5 Live Event Log

Bottom section showing a reverse-chronological stream of events:

- Wave start/completion events
- Individual device success/failure events
- Failure threshold warnings
- Pause/resume/cancel actions

Each event has a timestamp, colored dot (blue=info, green=success, red=error, amber=warning), and descriptive text. The log auto-scrolls to show new events. Up to 80 events are retained in the view; older events are in the audit log.

### 8.6 Pausing a Deployment

Click the **"Pause"** button (amber, with pause icon) in the deployment header. This:

1. Immediately stops sending new patch commands to agents.
2. Devices currently installing will complete their current patch installation.
3. No new waves are started.
4. The deployment status changes to "Paused".
5. The elapsed timer pauses.

Use pause when you notice unexpected issues and need time to investigate before deciding whether to continue or cancel.

### 8.7 Resuming a Deployment

On a paused deployment, the Pause button changes to **"Resume"** (with play icon). Clicking it:

1. Resumes the deployment from where it left off.
2. The current wave continues with remaining devices.
3. Status returns to "In Progress".
4. The timer resumes.

### 8.8 Cancelling a Deployment

Click the **"Cancel"** button (red, with X icon). A confirmation dialog appears. Confirming:

1. Stops all wave processing immediately.
2. All queued and in-progress device targets are marked as "Skipped".
3. Devices that already completed remain patched (cancellation is not a rollback).
4. The deployment status changes to "Cancelled".
5. An audit log entry records who cancelled and when.

### 8.9 Failure Threshold Breaches

If the cumulative failure rate exceeds the configured maximum (e.g., 5%), the system:

1. Automatically halts the deployment.
2. Status changes to "Failed".
3. A prominent red banner appears in the monitor.
4. The event log records the breach.
5. If auto-rollback is enabled, rollback begins (see 8.10).
6. An alert notification is sent (if configured in Settings).

### 8.10 Rollback Behavior

When auto-rollback triggers:

1. Failed devices receive a rollback command via WebSocket.
2. The agent attempts to revert the patch (package downgrade, uninstall).
3. Device status changes to "Rolled back" or "Rollback failed".
4. The deployment status shows "Rolling back" then "Rolled back".

Rollback is best-effort. Kernel patches that have been rebooted into, or Windows updates that have been finalized, may not be reversible. The event log records each device's rollback outcome.

### 8.11 WebSocket Connection Status

The live monitor depends on an active WebSocket connection. If the connection drops:

- A yellow "Reconnecting..." banner appears at the top.
- The system automatically reconnects with exponential backoff.
- During disconnection, data is not lost — the server buffers events.
- On reconnection, missed events are replayed and the UI catches up.

If reconnection fails after 10 attempts (about 5 minutes), a "Connection lost" banner appears with a manual "Reconnect" button.

---

## 9. Compliance and Reporting

### 9.1 Compliance Dashboard

Navigate to **Compliance** in the sidebar. The compliance dashboard shows fleet-wide patch compliance with:

- **Overall compliance rate**: Large number with trend arrow.
- **30-day compliance trend chart**: Line graph showing daily compliance percentage.
- **Breakdown by severity**: Compliance rates for critical, high, medium, and low patches separately.
- **Breakdown by environment**: Production vs. staging vs. development compliance.
- **Worst-performing devices**: Table of the 10 least compliant devices.
- **Overdue patches**: Patches that have exceeded their SLA window.

### 9.2 Compliance Rate Calculation

The compliance rate is calculated as:

```
Compliance % = (Installed patches) / (Installed + Pending + Failed patches) × 100
```

"Not applicable" patches are excluded. A device with 20 applicable patches where 18 are installed, 1 is pending, and 1 has failed has a compliance rate of 90%.

Fleet-wide compliance is the average across all active devices.

### 9.3 Per-Device Compliance

Each device's compliance rate is visible in the device list (compliance bar column) and device detail view. Click any device to see the full patch breakdown.

### 9.4 Per-Group Compliance

The compliance dashboard includes a group compliance table showing each device group's aggregate compliance rate. This helps identify which segments of your fleet need attention.

### 9.5 Per-Patch Coverage

For any individual patch, the catalog shows how many applicable devices have it installed. This is the "Affected" count minus the "Installed" count. Critical patches with low coverage are flagged in the dashboard.

### 9.6 Compliance Trend

The 30-day trend line chart shows how compliance has changed over time. A snapshot is captured daily at 01:00 UTC by a background task. The trend helps identify whether your patching program is improving or regressing.

### 9.7 SLA Reporting

SLA reports show how well your organization meets patching timelines:

- **Critical patches**: Target 72 hours from approval to 100% installation.
- **High patches**: Target 7 days.
- **Medium patches**: Target 30 days.
- **Low patches**: Target 90 days.

The report highlights patches that breached SLA with the number of days overdue and affected device count.

### 9.8 Exporting Reports

Click **"Export"** on the compliance dashboard. Options: CSV, PDF, or JSON.

PDF reports include charts and are formatted for printing or attaching to change management records.

### 9.9 Scheduled Report Generation

Administrators can configure automated report generation in Settings:

- **Daily compliance summary**: Emailed at a configured time.
- **Weekly executive report**: PDF with trend charts and SLA metrics.
- **Monthly audit report**: Full patch activity log.

Reports are delivered via email or saved to a configured network share.

---

## 10. Audit Log

### 10.1 What Gets Logged

Every mutation (create, update, delete) in the system is recorded:

- User authentication events (login success, failure, lockout)
- Device registration, modification, and decommissioning
- Patch approval, rejection, and status changes
- Deployment creation, execution, pause, resume, cancel
- User account creation, modification, role changes
- System setting changes
- Agent connections and disconnections

Each entry records: timestamp, user, action, resource type, resource ID, details (JSON), and IP address.

### 10.2 Viewing the Audit Log

Navigate to **Audit log** in the sidebar. The log displays entries in reverse chronological order (newest first).

Columns: Timestamp, User, Action, Resource, Details, IP Address.

### 10.3 Filtering Audit Entries

Filter by:
- **Date range**: Start and end date pickers.
- **User**: Dropdown of all users.
- **Action type**: Login, create, update, delete, deploy, approve, reject.
- **Resource type**: Device, patch, deployment, user, setting.
- **Search**: Free text search across action descriptions and details.

### 10.4 Audit Log Retention

Audit logs are partitioned by month in PostgreSQL. Default retention is 12 months. After 12 months, partitions are dropped automatically by a monthly maintenance task.

Administrators can change the retention period in Settings → Data Retention.

### 10.5 Exporting Audit Data

Click **"Export"** to download filtered audit entries as CSV or JSON. This is useful for compliance audits, incident investigations, or feeding into external SIEM systems.

---

## 11. User Management and RBAC

### 11.1 Role Definitions

| Role         | Description                                                  |
|--------------|--------------------------------------------------------------|
| Administrator| Full access. Can manage users, settings, approve deployments.|
| Operator     | Can manage devices, patches, and deployments. Cannot manage users or system settings. |
| Viewer       | Read-only access to all data. Cannot create, modify, or delete anything. |
| Agent        | Service account for device agents. Cannot access the UI.     |

### 11.2 Permission Matrix

| Action                         | Admin | Operator | Viewer |
|--------------------------------|-------|----------|--------|
| View dashboard                 | Yes   | Yes      | Yes    |
| View devices                   | Yes   | Yes      | Yes    |
| Add/edit/decommission devices  | Yes   | Yes      | No     |
| View patches                   | Yes   | Yes      | Yes    |
| Approve/reject patches         | Yes   | Yes      | No     |
| Create deployments             | Yes   | Yes      | No     |
| Execute/pause/cancel deploys   | Yes   | Yes      | No     |
| Delete deployments             | Yes   | No       | No     |
| View compliance reports        | Yes   | Yes      | Yes    |
| View audit log                 | Yes   | Yes      | Yes    |
| Manage users                   | Yes   | No       | No     |
| Manage system settings         | Yes   | No       | No     |
| Access Swagger API docs        | Yes   | Yes      | Yes    |

### 11.3 Creating a User

Administrators only:

1. Navigate to **Settings → Users**.
2. Click **"Create user"**.
3. Enter: username, email, first name, last name, role, department.
4. Set a temporary password (must meet password policy).
5. Check "Must change password on first login" (default: on).
6. Click **"Create"**.

The user receives their credentials via your organization's secure channel (not via PatchGuard — the system does not send emails for account creation).

### 11.4 Editing a User

1. Navigate to **Settings → Users**.
2. Click the user's row.
3. Editable: name, email, role, department, active status.
4. Click **"Save"**.

Role changes take effect on the user's next request (existing sessions are revalidated).

### 11.5 Deactivating a User

1. Edit the user and toggle "Active" to off, or click **"Deactivate"**.
2. The user can no longer log in.
3. Existing sessions are immediately invalidated.
4. The user's historical actions remain in the audit log.

### 11.6 Resetting a Password

Administrators can reset any user's password:

1. Navigate to the user's profile in **Settings → Users**.
2. Click **"Reset password"**.
3. Enter a new temporary password.
4. The "Must change password" flag is automatically set.

Users can change their own password from the avatar menu → "My profile".

### 11.7 Account Lockout Policy

After 5 consecutive failed login attempts, the account is locked for 30 minutes. During lockout:

- The user sees "Account locked. Try again later."
- The lockout is recorded in the audit log.
- An administrator can manually unlock the account from Settings → Users.

After the lockout period expires, the failed attempt counter resets.

### 11.8 LDAP/AD Group Mapping

When LDAP is configured, user roles are determined by Active Directory group membership at login time. The mapping is configured by the administrator:

1. Navigate to **Settings → Authentication → LDAP**.
2. Map AD group names to PatchGuard roles.
3. Default mapping: PatchMgr-Admins → Admin, PatchMgr-Operators → Operator, all others → Viewer.

Role changes in AD take effect at the user's next login. LDAP users cannot change their password in PatchGuard — they must use their organization's password change process.

### 11.9 API Keys for Agents

Each device has a unique API key used by its agent to authenticate WebSocket connections. API keys are:

- Generated automatically when a device is registered.
- 64-character random hex strings.
- Scoped to a single device — one key cannot be used for multiple devices.
- Revocable: decommissioning a device revokes its key.

To rotate an API key (e.g., if compromised):

1. Navigate to the device detail view.
2. Click **"Rotate API key"** in the settings section.
3. The old key is immediately invalidated.
4. Copy the new key and update the agent's configuration file on the device.

---

## 12. Agent Management

### 12.1 Agent Overview

The PatchGuard agent is a lightweight service that runs on each managed device. It:

- Maintains a persistent WebSocket connection to the PatchGuard server.
- Sends heartbeats every 60 seconds with CPU, RAM, and disk metrics.
- Reports system information (OS, hardware, installed packages).
- Executes patch installation commands received from the server.
- Reports installation results (success/failure) back to the server.

The agent runs as a system service (`patchguard-agent`) with root/SYSTEM privileges to install patches.

### 12.2 Agent Installation (Linux)

```bash
# Download the agent package
curl -O https://patchmgr.internal.corp/agent/patchguard-agent-linux-amd64.tar.gz

# Extract
tar xzf patchguard-agent-linux-amd64.tar.gz
cd patchguard-agent

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml — set server_url and api_key (see 12.5)

# Install as systemd service
sudo ./install.sh

# Verify
sudo systemctl status patchguard-agent
```

Supported distributions: Ubuntu 20.04+, RHEL 8+, Debian 11+, Amazon Linux 2023+.

### 12.3 Agent Installation (Windows)

```powershell
# Download the MSI installer
Invoke-WebRequest -Uri "https://patchmgr.internal.corp/agent/patchguard-agent-win64.msi" -OutFile "patchguard-agent.msi"

# Install with configuration
msiexec /i patchguard-agent.msi SERVER_URL="wss://patchmgr.internal.corp/ws/agent" API_KEY="your-device-api-key" /quiet

# Verify
Get-Service PatchGuardAgent
```

Supported: Windows Server 2016+, Windows 10/11 (21H2+).

### 12.4 Agent Installation (macOS)

```bash
# Download the PKG installer
curl -O https://patchmgr.internal.corp/agent/patchguard-agent-macos-universal.pkg

# Install
sudo installer -pkg patchguard-agent-macos-universal.pkg -target /

# Configure
sudo nano /etc/patchguard/config.yaml
# Set server_url and api_key

# Start
sudo launchctl load /Library/LaunchDaemons/com.patchguard.agent.plist
```

Supported: macOS 13 (Ventura)+.

### 12.5 Agent Configuration File

Location:
- Linux: `/etc/patchguard/config.yaml`
- Windows: `C:\ProgramData\PatchGuard\config.yaml`
- macOS: `/etc/patchguard/config.yaml`

```yaml
# PatchGuard Agent Configuration
server_url: "wss://patchmgr.internal.corp/ws/agent"
api_key: "your-64-char-api-key-here"

# Heartbeat interval in seconds (default: 60)
heartbeat_interval: 60

# Log level: debug, info, warn, error
log_level: info

# Log file location
log_file: "/var/log/patchguard/agent.log"

# Maximum log file size before rotation (MB)
log_max_size: 50

# TLS verification (set to false only for testing)
tls_verify: true

# Custom CA certificate path (for internal CAs)
ca_cert: "/etc/patchguard/ca.pem"

# Proxy settings (if agent connects through a proxy)
# proxy: "http://proxy.internal.corp:8080"
```

### 12.6 Agent Registration

When the agent starts for the first time with a valid API key:

1. It connects to the server via WebSocket.
2. The server validates the API key against the device database.
3. The agent sends a `system_info` message with OS, hardware, and software details.
4. The server updates the device record and marks it as "Online".
5. The agent begins sending heartbeats.

If the API key is invalid, the connection is rejected with code 4003.

### 12.7 Agent Heartbeat and Status

The agent sends a heartbeat every 60 seconds containing:

```json
{
  "type": "heartbeat",
  "timestamp": "2025-03-30T14:32:08Z",
  "cpu": 34.2,
  "mem": 61.0,
  "disk": 42.5
}
```

The server uses heartbeats to determine device status:
- **Online**: Heartbeat received within the last 5 minutes.
- **Offline**: No heartbeat for more than 5 minutes.

A background task runs every 5 minutes to mark stale devices as offline.

### 12.8 Agent Updates

When a new agent version is released:

1. The administrator uploads the new agent package to the PatchGuard server.
2. The server sends an `update_agent` command to connected agents.
3. The agent downloads the new version, verifies its checksum, and performs a self-update.
4. The agent restarts with the new version.
5. The device record updates with the new agent version.

Agents can also be updated manually by re-running the installer.

### 12.9 Agent Troubleshooting

**Agent won't connect**:
- Verify the `server_url` is correct and reachable from the device.
- Check TLS certificate validity: `curl -v wss://patchmgr.internal.corp/ws/agent`.
- Verify the API key matches the device record in PatchGuard.
- Check agent logs: `sudo journalctl -u patchguard-agent -f` (Linux).

**Agent shows as offline despite running**:
- Check firewall rules: port 443 must be open outbound.
- Check proxy settings if applicable.
- Verify WebSocket connections are not being terminated by a network appliance.

**Patches fail to install**:
- Check the agent has root/SYSTEM privileges.
- Check disk space (minimum 1 GB free required).
- Check the agent log for specific error messages.
- Verify package repositories are accessible from the device.

---

## 13. System Settings

Settings are accessible to administrators only via **Settings** in the sidebar.

### 13.1 General Settings

- **Organization name**: Displayed in reports and the login page.
- **Default timezone**: Used for scheduling and log display (default: UTC).
- **Session timeout**: Inactivity timeout in minutes (default: 30).
- **Require deployment approval**: Toggle. When on, deployments must be approved by an admin before execution.
- **Default SLA windows**: Configure patching SLA targets per severity level.

### 13.2 Vendor Feed Configuration

Configure which vendor feeds PatchGuard syncs with:

| Setting          | Description                                    |
|------------------|------------------------------------------------|
| Feed URL         | The vendor's advisory feed endpoint            |
| Sync interval    | How often to check for new patches (default: 6h)|
| Enabled          | Toggle feed on/off                             |
| Auto-import      | Automatically import new patches (vs. manual)  |

Supported feeds: Canonical USN, Red Hat RHSA, Microsoft WSUS. Additional feeds can be added via custom importers.

Click **"Sync now"** to trigger an immediate sync.

### 13.3 Notification Settings

Configure how PatchGuard alerts you to important events:

- **New critical patches**: Alert when a critical-severity patch is imported.
- **Deployment failures**: Alert when a deployment exceeds its failure threshold.
- **Device offline**: Alert when a production device goes offline.
- **Compliance threshold**: Alert when fleet compliance drops below a configured level.

### 13.4 Email / Webhook Alerts

**Email**: Configure SMTP settings (server, port, TLS, credentials, from address). Test with "Send test email".

**Webhook**: Configure a URL to receive POST requests with JSON payloads for each alert. Compatible with Slack incoming webhooks, Microsoft Teams, PagerDuty, and generic HTTP endpoints.

### 13.5 Maintenance Window Presets

Define reusable maintenance windows:

- **Name**: e.g., "Nightly window", "Weekend window"
- **Schedule**: Cron expression or day/time specification
- **Duration**: How long the window stays open
- **Timezone**: Window-specific timezone

These presets appear in the deployment wizard's scheduling dropdown.

### 13.6 Data Retention Policies

Configure how long different data types are retained:

| Data Type         | Default Retention | Configurable |
|-------------------|-------------------|--------------|
| Audit log         | 12 months         | Yes          |
| Deployment history| 24 months         | Yes          |
| Device metrics    | 30 days           | Yes          |
| Patch status      | Indefinite        | No           |
| Decommissioned    | 6 months          | Yes          |

A monthly cleanup task removes expired data.

### 13.7 TLS Certificate Management

View the current TLS certificate details (issuer, expiration date, fingerprint). Upload a new certificate and key when the current one approaches expiration. PatchGuard warns administrators 30 days before certificate expiry.

### 13.8 Backup and Restore

**Automated backups**: A daily `pg_dump` runs at 03:00 UTC and saves to the configured backup directory. The last 7 daily backups and 4 weekly backups are retained.

**Manual backup**: Click **"Backup now"** to trigger an immediate database dump.

**Restore**: Stop the PatchGuard services, restore the database from a backup file, then restart services. Detailed instructions are in the admin deployment guide.

### 13.9 System Health Check

The health check page shows the status of all system components:

- **PostgreSQL**: Connection status, query latency, replication lag
- **Redis**: Connection status, memory usage, connected clients
- **Celery workers**: Worker count, queue depth per queue, task success rate
- **WebSocket connections**: Agent count, dashboard count
- **Disk space**: Available space on the server

Each component shows a green/amber/red status indicator. Click any component for detailed metrics.

Access the health check API at: `GET /api/health/`

---

## 14. API Reference

### 14.1 Authentication Endpoints

| Method | Endpoint               | Description              |
|--------|------------------------|--------------------------|
| POST   | `/api/v1/auth/login/`  | Get JWT access + refresh |
| POST   | `/api/v1/auth/refresh/`| Refresh access token     |
| POST   | `/api/v1/auth/logout/` | Blacklist refresh token  |

### 14.2 Device Endpoints

| Method | Endpoint                          | Description                  |
|--------|-----------------------------------|------------------------------|
| GET    | `/api/v1/devices/`                | List devices (paginated)     |
| POST   | `/api/v1/devices/`                | Register a device            |
| GET    | `/api/v1/devices/{id}/`           | Device detail                |
| PATCH  | `/api/v1/devices/{id}/`           | Update device                |
| GET    | `/api/v1/devices/{id}/compliance/`| Device compliance summary    |
| POST   | `/api/v1/devices/bulk-tag/`       | Bulk add/remove tags         |
| GET    | `/api/v1/device-groups/`          | List groups                  |
| POST   | `/api/v1/device-groups/`          | Create group                 |
| GET    | `/api/v1/device-groups/{id}/devices/` | List group members      |

### 14.3 Patch Endpoints

| Method | Endpoint                          | Description                  |
|--------|-----------------------------------|------------------------------|
| GET    | `/api/v1/patches/`                | List patches (paginated)     |
| GET    | `/api/v1/patches/{id}/`           | Patch detail                 |
| POST   | `/api/v1/patches/{id}/approve/`   | Approve a patch              |
| POST   | `/api/v1/patches/{id}/reject/`    | Reject a patch               |

### 14.4 Deployment Endpoints

| Method | Endpoint                              | Description                  |
|--------|---------------------------------------|------------------------------|
| GET    | `/api/v1/deployments/`                | List deployments             |
| POST   | `/api/v1/deployments/`                | Create deployment            |
| GET    | `/api/v1/deployments/{id}/`           | Deployment detail            |
| POST   | `/api/v1/deployments/{id}/approve/`   | Approve deployment           |
| POST   | `/api/v1/deployments/{id}/execute/`   | Execute deployment           |
| POST   | `/api/v1/deployments/{id}/pause/`     | Pause deployment             |
| POST   | `/api/v1/deployments/{id}/cancel/`    | Cancel deployment            |
| GET    | `/api/v1/deployments/{id}/progress/`  | Live progress data           |

### 14.5 Report Endpoints

| Method | Endpoint                              | Description                  |
|--------|---------------------------------------|------------------------------|
| GET    | `/api/v1/reports/dashboard-stats/`    | Dashboard KPI data           |
| GET    | `/api/v1/reports/compliance/`         | Fleet compliance report      |
| GET    | `/api/v1/reports/compliance/trend/`   | 30-day compliance trend      |
| GET    | `/api/v1/reports/sla/`               | SLA adherence report         |

### 14.6 Swagger UI Access

Interactive API documentation is available at:

- **Swagger UI**: `https://patchmgr.internal.corp/api/docs/`
- **ReDoc**: `https://patchmgr.internal.corp/api/redoc/`
- **OpenAPI schema (JSON)**: `https://patchmgr.internal.corp/api/schema/`
- **FastAPI real-time docs**: `https://patchmgr.internal.corp/rt/docs`

Authenticate in Swagger by clicking "Authorize" and entering your JWT token (obtained from the login endpoint).

### 14.7 Rate Limiting

| Endpoint Category  | Limit              |
|--------------------|--------------------|
| Authentication     | 5 requests/minute  |
| General API        | 30 requests/second |
| Agent check-in     | 50 requests/second |
| Report generation  | 5 requests/minute  |

Exceeding rate limits returns HTTP 429 with a `Retry-After` header.

### 14.8 Error Codes

| HTTP Code | Meaning                                      |
|-----------|----------------------------------------------|
| 400       | Bad request — invalid parameters             |
| 401       | Unauthorized — invalid or expired token      |
| 403       | Forbidden — insufficient role/permissions    |
| 404       | Resource not found                           |
| 409       | Conflict — e.g., duplicate hostname          |
| 422       | Validation error — detailed in response body |
| 429       | Rate limit exceeded                          |
| 500       | Server error — check logs                    |

---

## 15. Troubleshooting

### 15.1 Login Issues

**"Invalid credentials"**: Verify username and password. For LDAP users, ensure you're using your domain username (not email). Check Caps Lock.

**"Account locked"**: Wait 30 minutes or ask an administrator to unlock your account from Settings → Users.

**"Token expired" after login**: The server clock may be skewed. JWT tokens are time-sensitive — ensure the server and client clocks are within 60 seconds of each other. Contact your administrator.

### 15.2 Agent Connectivity Problems

**Agent cannot reach server**: Check DNS resolution (`nslookup patchmgr.internal.corp`), firewall rules (port 443 outbound), and proxy configuration.

**Intermittent disconnections**: Check for network appliances (load balancers, firewalls) that terminate idle WebSocket connections. The agent sends heartbeats every 60 seconds — ensure your network allows idle connections of at least 90 seconds.

**Certificate errors**: If using an internal CA, ensure the CA certificate is installed on the device and referenced in the agent's `ca_cert` configuration.

### 15.3 WebSocket Connection Drops

**Dashboard shows "Reconnecting..."**: Usually temporary — wait for automatic reconnection. If persistent, check browser console for WebSocket errors. Try hard-refreshing the page (Ctrl+Shift+R).

**Nginx 504 Gateway Timeout on WebSocket**: Ensure `proxy_read_timeout` is set to 86400s (24 hours) in the Nginx configuration for WebSocket endpoints.

### 15.4 Deployment Stuck in Progress

If a deployment shows "In Progress" but no devices are being processed:

1. Check Celery worker status: the worker may have crashed.
2. Check Redis connectivity: the Celery broker may be unreachable.
3. Check for paused state that wasn't reflected in the UI.
4. As a last resort, cancel the deployment and create a new one.

### 15.5 Patch Installation Failures

Common failure reasons:

- **Dependency conflict**: Another package requires a conflicting version. Check the agent log for the specific package conflict.
- **Disk space**: Insufficient free disk. Ensure at least 1 GB free.
- **Repository unreachable**: The device cannot reach the package repository. Check network and proxy settings.
- **Permission denied**: The agent may not have root/SYSTEM privileges. Verify the service is running as the correct user.
- **Reboot required**: A previous patch requires a reboot before the new patch can be installed.

### 15.6 High Database Load

Symptoms: slow page loads, API timeouts.

Solutions:
1. Check PgBouncer pool utilization — increase `DEFAULT_POOL_SIZE` if saturated.
2. Ensure reporting queries are routing to the read replica (check `DATABASE_ROUTERS` configuration).
3. Check for missing indexes on frequently queried columns.
4. Review slow query log: queries over 500ms are logged automatically.

### 15.7 Redis Connection Errors

Symptoms: dashboard not updating, deployments not starting.

Solutions:
1. Check Redis is running: `redis-cli ping` should return `PONG`.
2. Check memory: Redis may have evicted keys if at `maxmemory`. Increase the limit or review key usage.
3. Check connections: `redis-cli info clients` shows connected client count.

### 15.8 Celery Worker Issues

Symptoms: deployments don't execute, scheduled tasks don't run.

Solutions:
1. Check worker status: `celery -A config.celery_app inspect active`.
2. Check queue depth: `celery -A config.celery_app inspect reserved`.
3. Restart workers if stuck: `docker compose restart celery-worker`.
4. Check for task time limit exceeded: tasks have a 1-hour hard limit.

### 15.9 Certificate Expiration

PatchGuard warns administrators 30 days before TLS certificate expiry. If the certificate has already expired:

1. Agents will disconnect (TLS verification fails).
2. Browser will show a security warning.
3. Upload a new certificate via Settings → TLS or replace the files in `nginx/ssl/`.
4. Restart Nginx: `docker compose restart nginx`.

### 15.10 Performance Degradation

If the system feels slow:

1. Check **Settings → System Health** for component-level status.
2. Monitor PostgreSQL query times — enable `log_min_duration_statement = 200` for slow query logging.
3. Check Celery queue depth — a large backlog indicates worker capacity issues. Scale up workers.
4. Check browser developer tools Network tab for slow API calls.
5. Verify Redis cache hit rate — low hit rate means cached data isn't being used effectively.

---

## 16. Glossary

| Term                | Definition                                                                  |
|---------------------|-----------------------------------------------------------------------------|
| Agent               | Lightweight software running on each managed device                        |
| Canary              | A small subset of devices that receive a patch first for testing           |
| Compliance rate     | Percentage of applicable patches that are installed                        |
| CVE                 | Common Vulnerabilities and Exposures — unique vulnerability identifier     |
| Deployment          | A planned rollout of one or more patches to a set of devices               |
| Device group        | A collection of devices used for targeting deployments                     |
| Dynamic group       | A group whose membership is determined by rules                           |
| Heartbeat           | Periodic status message sent by agent to server                           |
| JWT                 | JSON Web Token — used for API authentication                              |
| KB article          | Microsoft Knowledge Base article describing a patch                       |
| Maintenance window  | Scheduled time period during which deployments may execute                 |
| RBAC                | Role-Based Access Control — permissions based on user role                 |
| Rollback            | Reverting a patch installation to the previous state                      |
| Rolling deployment  | Deploying in sequential waves with delays between them                    |
| SLA                 | Service Level Agreement — target timeframe for patch installation         |
| Static group        | A group with manually managed device membership                          |
| Superseded          | A patch that has been replaced by a newer version                         |
| Wave                | A batch of devices within a deployment that are patched together          |
| WebSocket           | Persistent bidirectional connection for real-time communication           |

---

*PatchGuard User Guide v1.0 — Confidential — For internal use only*
