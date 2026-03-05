import { Component, OnInit, signal, inject } from '@angular/core';
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

  loading = signal(true);
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

  tabs = [
    { label: 'PATCHES.AWAITING_REVIEW', value: 'imported', count: 0 },
    { label: 'PATCHES.APPROVED', value: 'approved', count: 0 },
    { label: 'PATCHES.ALL_PATCHES', value: 'all', count: 0 },
    { label: 'PATCHES.CRITICAL', value: 'critical_sev', count: 0 },
  ];

  totalPages() {
    return Math.ceil(this.total() / this.pageSize);
  }

  ngOnInit() {
    this.loadPatches();
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
    this.selectedPatch.set(p);
  }

  approve(p: any) {
    this.pendingPatch = p;
    this.confirmAction = 'approve';
    this.confirmMsg = `Approve patch "${p.title}"? This will make it available for deployment.`;
    this.confirmVisible.set(true);
  }
  reject(p: any) {
    this.pendingPatch = p;
    this.confirmAction = 'reject';
    this.confirmMsg = `Reject patch "${p.title}"? It will not be available for deployment.`;
    this.confirmVisible.set(true);
  }
  doConfirm() {
    this.confirmVisible.set(false);
    if (!this.pendingPatch) return;
    const obs =
      this.confirmAction === 'approve'
        ? this.patchSvc.approvePatch(this.pendingPatch.id)
        : this.patchSvc.rejectPatch(this.pendingPatch.id);
    obs.subscribe({
      next: () => {
        this.ns.success('Done', `Patch ${this.confirmAction}d.`);
        this.loadPatches();
      },
      error: () => this.ns.error('Error', `Failed to ${this.confirmAction} patch.`),
    });
  }
  bulkApprove() {
    const ids = Array.from(this.selectedIds());
    this.patchSvc.bulkApprove(ids).subscribe({
      next: () => {
        this.ns.success('Approved', `${ids.length} patches approved.`);
        this.loadPatches();
        this.clearSelection();
      },
      error: () => this.ns.error('Error', 'Bulk approve failed.'),
    });
  }
}
