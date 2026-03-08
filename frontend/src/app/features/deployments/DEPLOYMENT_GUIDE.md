# PatchGuard Deployment Guide

This document provides a comprehensive overview of how to manage patch deployments in PatchGuard, from creating a new deployment via the Wizard to monitoring real-time execution.

## Table of Contents
- [Overview](#overview)
- [Creating a New Deployment](#creating-a-new-deployment)
  - [Step 1: Patch Selection](#step-1-patch-selection)
  - [Step 2: Target Selection](#step-2-target-selection)
  - [Step 3: Strategy Selection](#step-3-strategy-selection)
  - [Step 4: Review and Schedule](#step-4-review-and-schedule)
- [Rollout Strategies](#rollout-strategies)
- [Live Monitoring](#live-monitoring)
- [Post-Deployment Actions](#post-deployment-actions)

---

## Overview

The Deployment Module is the core of PatchGuard's orchestration engine. It allows administrators and operators to group approved patches and servers into a single execution unit with controlled rollout strategies.

---

## Creating a New Deployment

The **Deployment Wizard** is a 4-step process designed to ensure safety and precision.

### Step 1: Patch Selection
Select the patches you wish to deploy. 
- You can only select patches that have been **Approved**.
- Use the filters to quickly find **Critical** or **High-risk** patches.
- The sidebar will track your selection and highlight if any selected patches require a reboot.

### Step 2: Target Selection
Choose the **Device Groups** that will receive the patches.
- PatchGuard calculates the total number of affected devices in real-time.
- You can filter groups by environment (e.g., Production, Staging).

### Step 3: Strategy Selection
Choose how the patches will be rolled out.
- **Immediate**: Deploys to all devices at once. Use with caution.
- **Canary**: Deploys to a small percentage first. Execution halts if the failure rate exceeds your threshold.
- **Rolling**: Deploys wave-by-wave with a configurable time delay.

> [!TIP]
> Use the **Maintenance Window** option to ensure deployments only occur during approved time slots (e.g., 02:00—06:00 UTC).

### Step 4: Review and Schedule
A final summary of your deployment.
- Review the **Estimated Duration** and **Max Failure Rate**.
- You must explicitly confirm change management approval before scheduling.

---

## Rollout Strategies

| Strategy | Speed | Risk | Best For |
| :--- | :--- | :--- | :--- |
| **Immediate** | High | High | Emergency hotfixes, Dev environments |
| **Canary** | Medium | Low | Initial production rollout, high-risk patches |
| **Rolling** | Medium | Medium | Standard monthly patching |

---

## Live Monitoring

Once a deployment starts, you are redirected to the **Live Monitor**.

- **Progress Tracking**: Holistic view of success vs. failure rates.
- **Wave Management**: See exactly which wave is currently active and how many devices remain.
- **Device Map**: A visual heat-map showing the status of every individual device.
- **Event Log**: Real-time stream of agent activity and error messages via WebSockets.

> [!IMPORTANT]
> If a deployment hits its **Max Failure Rate**, PatchGuard will automatically halt execution to prevent widespread outages. You can then manually choose to **Resume** or **Rollback**.

---

## Post-Deployment Actions

After a deployment reaches a terminal state (Completed or Failed), you can:
- **View Audit Logs**: See exactly who approved and started the deployment.
- **Rollback**: (If supported by the patch) Initiate a removal wave to return devices to their previous state.
- **Download Reports**: Export a summary for compliance reporting.
