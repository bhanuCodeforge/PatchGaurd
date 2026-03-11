import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { PatchService } from '../../core/services/patch.service';
import { NotificationService } from '../../core/services/notification.service';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { PatchApprovalModalComponent } from '../../shared/components/patch-approval-modal/patch-approval-modal.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';
import { AuthService } from '../../core/auth/auth.service';
import { DeviceService } from '../../core/services/device.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-patch-catalog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule,
    LoadingSkeletonComponent,
    EmptyStateComponent,
    PatchApprovalModalComponent,
    RelativeTimePipe,
  ],
  templateUrl: './patch-catalog.component.html',
  styleUrl: './patch-catalog.component.scss',
})
export class PatchCatalogComponent implements OnInit {
  private patchSvc = inject(PatchService);
  private ns = inject(NotificationService);
  private auth = inject(AuthService);
  private deviceSvc = inject(DeviceService);
  private router = inject(Router);

  canWrite = computed(() => this.auth.isOperatorOrAbove());

  loading = signal(true);
  statsLoading = signal(true);
  patches = signal<any[]>([]);
  total = signal(0);
  page = signal(1);
  pageSize = 25;
  rows = Array(8)
    .fill(0)
    .map((_, i) => i);

  activeTab = 'all';
  searchTerm = '';
  severityFilter = '';
  vendorFilter = '';
  selectedIds = signal<Set<string>>(new Set());
  selectedPatch = signal<any>(null);

  confirmVisible = signal(false);
  confirmAction: 'approve' | 'reject' = 'approve';
  confirmMsg = '';
  private pendingPatch: any = null;

  bulkRejectVisible = signal(false);
  bulkRejectReason = '';

  addPatchVisible = signal(false);
  newPatch = {
    vendor_id: '',
    title: '',
    severity: 'medium',
    vendor: 'Microsoft',
    applicable_os: [] as string[],
    description: '',
    cve_ids: [] as string[],
    requires_reboot: false,
  };
  newPatchCveInput = '';
  newPatchOsInput = '';

  stats = signal<any>(null);

  tabs = signal([
    { label: 'UI.u_awaiting_review', value: 'imported', count: 0 },
    { label: 'UI.u_approved', value: 'approved', count: 0 },
    { label: 'UI.u_all_patches', value: 'all', count: 0 },
    { label: 'UI.u_critical', value: 'critical_sev', count: 0 },
  ]);

  totalPages() {
    return Math.ceil(this.total() / this.pageSize);
  }

  pageNumbers(): number[] {
    const total = this.totalPages();
    const current = this.page();
    const pages: number[] = [];
    for (let i = Math.max(1, current - 2); i <= Math.min(total, current + 2); i++) pages.push(i);
    return pages;
  }

  ngOnInit() {
    this.loadPatches();
    this.loadStats();
  }

  loadStats() {
    this.statsLoading.set(true);
    this.patchSvc.getPatchStats().subscribe({
      next: (s) => {
        this.stats.set(s);
        // Update tab counts
        const bySeverity = Object.fromEntries(
          (s.by_severity || []).map((x: any) => [x.severity, x.count]),
        );
        const byStatus = Object.fromEntries(
          (s.by_status || []).map((x: any) => [x.status, x.count]),
        );
        this.tabs.update((tabs) =>
          tabs.map((t) => ({
            ...t,
            count:
              t.value === 'imported'
                ? byStatus['imported'] || 0
                : t.value === 'approved'
                  ? byStatus['approved'] || 0
                  : t.value === 'all'
                    ? s.total || 0
                    : t.value === 'critical_sev'
                      ? bySeverity['critical'] || 0
                      : 0,
          })),
        );
        this.statsLoading.set(false);
      },
      error: () => this.statsLoading.set(false),
    });
  }

  loadPatches() {
    this.loading.set(true);
    const params: any = { page: this.page(), page_size: this.pageSize };
    if (this.searchTerm) params.search = this.searchTerm;
    if (this.severityFilter) params.severity = this.severityFilter;
    if (this.vendorFilter) params.vendor = this.vendorFilter;
    if (this.activeTab === 'imported') params.status = 'imported';
    else if (this.activeTab === 'approved') params.status = 'approved';
    else if (this.activeTab === 'critical_sev') params.severity = 'critical';
    this.patchSvc.getPatches(params).subscribe({
      next: (r) => {
        this.patches.set(r.results ?? []);
        this.total.set(r.count ?? 0);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  setTab(v: string) {
    this.activeTab = v;
    this.page.set(1);
    this.loadPatches();
  }
  setPage(p: number) {
    this.page.set(p);
    this.loadPatches();
  }

  toggleSelect(id: string) {
    this.selectedIds.update((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  }
  toggleAll(e: Event) {
    const checked = (e.target as HTMLInputElement).checked;
    this.selectedIds.set(checked ? new Set(this.patches().map((p) => p.id)) : new Set());
  }
  clearSelection() {
    this.selectedIds.set(new Set());
  }
  openPanel(p: any) {
    // Show list-level data immediately, then fetch full detail
    this.selectedPatch.set(p);
    this.patchSvc.getPatchById(p.id).subscribe({
      next: (detail) => this.selectedPatch.set(detail),
      error: () => {} // Keep list-level data on error
    });
  }

  markReview(p: any) {
    this.patchSvc.reviewPatch(p.id).subscribe({
      next: () => {
        this.ns.success('Reviewed', `Patch ${p.vendor_id} marked as reviewed.`);
        this.loadPatches();
        this.loadStats();
      },
      error: (err: any) => {
        const msg = err?.error?.detail || err?.error?.error || 'Failed to mark patch as reviewed.';
        this.ns.error('Error', msg);
      },
    });
  }

  /** Count for approved patches from stats */
  approvedCount(): number {
    const s = this.stats();
    if (!s) return 0;
    const byStatus: any[] = s.by_status || [];
    return byStatus.find((x: any) => x.status === 'approved')?.count ?? 0;
  }

  /** First CVE id from the array, or vendor_id as fallback */
  getCveLabel(p: any): string {
    const ids = p.cve_ids;
    if (Array.isArray(ids) && ids.length) return ids[0];
    return p.vendor_id || '—';
  }

  /** Comma-joined OS list */
  getOsLabel(p: any): string {
    const os = p.applicable_os;
    if (Array.isArray(os)) return os.join(', ');
    return os || '—';
  }

  approve(p: any) {
    this.pendingPatch = p;
    this.confirmAction = 'approve';
    this.confirmMsg = `Approve "${p.title}"? This will make it available for deployment.`;
    this.confirmVisible.set(true);
  }
  reject(p: any) {
    this.pendingPatch = p;
    this.confirmAction = 'reject';
    this.confirmMsg = `Reject "${p.title}"? It will be excluded from deployments.`;
    this.confirmVisible.set(true);
  }

  doConfirm(reason: string = '') {
    this.confirmVisible.set(false);
    if (!this.pendingPatch) return;
    const obs =
      this.confirmAction === 'approve'
        ? this.patchSvc.approvePatch(this.pendingPatch.id, reason)
        : this.patchSvc.rejectPatch(this.pendingPatch.id, reason);
    obs.subscribe({
      next: () => {
        this.ns.success('Done', `Patch ${this.confirmAction}d successfully.`);
        this.loadPatches();
        this.loadStats();
        if (this.selectedPatch()?.id === this.pendingPatch.id) {
          this.selectedPatch.set(null);
        }
      },
      error: (err: any) => {
        const msg =
          err?.error?.detail || err?.error?.error || `Failed to ${this.confirmAction} patch.`;
        this.ns.error('Error', msg);
      },
    });
  }

  bulkApprove() {
    const ids = Array.from(this.selectedIds());
    this.patchSvc.bulkApprove(ids).subscribe({
      next: (res: any) => {
        this.ns.success('Bulk Approved', res?.status || `${ids.length} patches approved.`);
        this.loadPatches();
        this.loadStats();
        this.clearSelection();
      },
      error: () => this.ns.error('Error', 'Bulk approve failed.'),
    });
  }

  openBulkReject() {
    this.bulkRejectReason = '';
    this.bulkRejectVisible.set(true);
  }

  bulkReject() {
    const ids = Array.from(this.selectedIds());
    const reason = this.bulkRejectReason.trim();
    if (!reason) {
      this.ns.error('Required', 'A rejection reason is required.');
      return;
    }
    this.bulkRejectVisible.set(false);
    this.patchSvc.bulkReject(ids, reason).subscribe({
      next: (res: any) => {
        this.ns.success('Bulk Rejected', res?.status || `${ids.length} patches rejected.`);
        this.loadPatches();
        this.loadStats();
        this.clearSelection();
      },
      error: () => this.ns.error('Error', 'Bulk reject failed.'),
    });
  }

  triggerGlobalScan() {
    this.deviceSvc.triggerGlobalScan().subscribe({
      next: (res: any) => {
        this.ns.success('Scan Triggered', res.status || 'Fleet-wide scan initiated.');
        // Refresh list after a delay to catch early results
        setTimeout(() => this.loadPatches(), 3000);
      },
      error: () => this.ns.error('Error', 'Failed to trigger fleet scan.'),
    });
  }

  createDeployment() {
    const ids = Array.from(this.selectedIds());
    if (ids.length === 0) return;

    // Filter only approved patches for the deployment wizard
    const approvedIds = this.patches()
      .filter((p) => ids.includes(p.id) && p.status === 'approved')
      .map((p) => p.id);

    if (approvedIds.length === 0) {
      this.ns.warning(
        'Action Required',
        'Only approved patches can be deployed. Please approve your selection first.',
      );
      return;
    }

    this.router.navigate(['/deployments/new'], {
      state: { patch_ids: approvedIds },
    });
  }

  resetFilters() {
    this.searchTerm = '';
    this.severityFilter = '';
    this.vendorFilter = '';
    this.setTab('all');
  }

  openAddPatch() {
    this.newPatch = {
      vendor_id: '',
      title: '',
      severity: 'medium',
      vendor: 'Microsoft',
      applicable_os: [],
      description: '',
      cve_ids: [],
      requires_reboot: false,
    };
    this.newPatchCveInput = '';
    this.newPatchOsInput = '';
    this.addPatchVisible.set(true);
  }

  addCveId() {
    const id = this.newPatchCveInput.trim();
    if (id && !this.newPatch.cve_ids.includes(id)) {
      this.newPatch.cve_ids.push(id);
    }
    this.newPatchCveInput = '';
  }

  removeCveId(id: string) {
    this.newPatch.cve_ids = this.newPatch.cve_ids.filter((c) => c !== id);
  }

  addOs() {
    const os = this.newPatchOsInput.trim();
    if (os && !this.newPatch.applicable_os.includes(os)) {
      this.newPatch.applicable_os.push(os);
    }
    this.newPatchOsInput = '';
  }

  removeOs(os: string) {
    this.newPatch.applicable_os = this.newPatch.applicable_os.filter((o) => o !== os);
  }

  submitNewPatch() {
    if (!this.newPatch.vendor_id.trim() || !this.newPatch.title.trim()) {
      this.ns.error('Validation', 'Vendor ID and Title are required.');
      return;
    }
    this.patchSvc.createPatch(this.newPatch).subscribe({
      next: () => {
        this.ns.success('Created', 'Patch added successfully.');
        this.addPatchVisible.set(false);
        this.loadPatches();
        this.loadStats();
      },
      error: (err: any) => {
        const msg = err?.error?.detail || err?.error?.vendor_id?.[0] || JSON.stringify(err?.error) || 'Failed to create patch.';
        this.ns.error('Error', msg);
      },
    });
  }
}
