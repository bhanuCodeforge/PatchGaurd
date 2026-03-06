import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { PatchService } from '../../core/services/patch.service';
import { NotificationService } from '../../core/services/notification.service';
import { StatusBadgeComponent } from '../../shared/components/status-badge.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-patch-catalog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule,
    LoadingSkeletonComponent,
    EmptyStateComponent,
    ConfirmDialogComponent,
    RelativeTimePipe,
  ],
  templateUrl: './patch-catalog.component.html',
  styleUrl: './patch-catalog.component.scss',
})
export class PatchCatalogComponent implements OnInit {
  private patchSvc = inject(PatchService);
  private ns = inject(NotificationService);
  private auth = inject(AuthService);

  canWrite = computed(() => this.auth.isOperatorOrAbove());

  loading = signal(true);
  statsLoading = signal(true);
  patches = signal<any[]>([]);
  total = signal(0);
  page = signal(1);
  pageSize = 25;
  rows = Array(8).fill(0).map((_, i) => i);

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

  stats = signal<any>(null);

  tabs = signal([
    { label: 'PATCHES.AWAITING_REVIEW', value: 'imported',     count: 0 },
    { label: 'PATCHES.APPROVED',        value: 'approved',     count: 0 },
    { label: 'PATCHES.ALL_PATCHES',     value: 'all',          count: 0 },
    { label: 'PATCHES.CRITICAL',        value: 'critical_sev', count: 0 },
  ]);

  totalPages() { return Math.ceil(this.total() / this.pageSize); }

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
        const bySeverity = Object.fromEntries((s.by_severity || []).map((x: any) => [x.severity, x.count]));
        const byStatus   = Object.fromEntries((s.by_status   || []).map((x: any) => [x.status,   x.count]));
        this.tabs.update(tabs => tabs.map(t => ({
          ...t,
          count:
            t.value === 'imported'     ? (byStatus['imported']  || 0) :
            t.value === 'approved'     ? (byStatus['approved']  || 0) :
            t.value === 'all'          ? (s.total               || 0) :
            t.value === 'critical_sev' ? (bySeverity['critical'] || 0) : 0,
        })));
        this.statsLoading.set(false);
      },
      error: () => this.statsLoading.set(false),
    });
  }

  loadPatches() {
    this.loading.set(true);
    const params: any = { page: this.page(), page_size: this.pageSize };
    if (this.searchTerm)    params.search   = this.searchTerm;
    if (this.severityFilter) params.severity = this.severityFilter;
    if (this.vendorFilter)   params.vendor   = this.vendorFilter;
    if (this.activeTab === 'imported')     params.status   = 'imported';
    else if (this.activeTab === 'approved')    params.status   = 'approved';
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

  setTab(v: string) { this.activeTab = v; this.page.set(1); this.loadPatches(); }
  setPage(p: number) { this.page.set(p); this.loadPatches(); }

  toggleSelect(id: string) {
    this.selectedIds.update(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }
  toggleAll(e: Event) {
    const checked = (e.target as HTMLInputElement).checked;
    this.selectedIds.set(checked ? new Set(this.patches().map(p => p.id)) : new Set());
  }
  clearSelection() { this.selectedIds.set(new Set()); }
  openPanel(p: any) { this.selectedPatch.set(p); }

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
  doConfirm() {
    this.confirmVisible.set(false);
    if (!this.pendingPatch) return;
    const obs = this.confirmAction === 'approve'
      ? this.patchSvc.approvePatch(this.pendingPatch.id)
      : this.patchSvc.rejectPatch(this.pendingPatch.id);
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
        const msg = err?.error?.detail || err?.error?.error || `Failed to ${this.confirmAction} patch.`;
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
}
