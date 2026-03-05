# Task 7.9 — Deployment Wizard (Multi-Step)

**Time**: 4 hours  
**Dependencies**: 7.4, 7.2  
**Status**: ⬜ Not Started  
**Files**: `frontend/src/app/features/deployments/`

---

## AI Prompt

```
Implement the PatchGuard deployment wizard as a multi-step form.

4 steps:
1. Select patches (search, filter, checkbox, "Select all critical")
2. Select target groups (search, checkbox, device counts)
3. Configure strategy (Immediate/Canary/Rolling cards, parameter sliders)
4. Review (full summary, warnings, deploy now / schedule)

Sticky sidebar with live deployment summary. Step validation. Reactive forms or signals.
Route: /deployments/new
```

---

## Acceptance Criteria

- [ ] All 4 steps render correctly
- [ ] Step navigation with validation works
- [ ] Strategy cards are selectable
- [ ] Sliders update summary in real time
- [ ] Warning banner shows for production + reboot
- [ ] Submit creates deployment via API
- [ ] Cancel with confirmation dialog

## Files Created/Modified

- [ ] `frontend/src/app/features/deployments/deployment-wizard.component.ts`
- [ ] `frontend/src/app/features/deployments/steps/` (step components)

## Completion Log

<!-- Record completion date, notes, and any deviations -->
