import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { debounceTime, Subject, Subscription } from 'rxjs';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { DeviceDetailComponent } from '../devices-detail/device-detail.component';
import { DeviceEditComponent } from '../device-edit/device-edit.component';
import { WebsocketService } from '../../../core/services/websocket.service';

@Component({
  selector: 'app-device-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    TranslateModule,
    StatusBadgeComponent,
    LoadingSkeletonComponent,
    EmptyStateComponent,
    DeviceDetailComponent,
    DeviceEditComponent,
  ],
  templateUrl: './device-list.component.html',
  styleUrl: './device-list.component.scss',
})
export class DeviceListComponent implements OnInit, OnDestroy {
  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);
  private ws = inject(WebsocketService);
  private wsSub?: Subscription;
  Math = Math;

  loading = signal(true);
  devices = signal<any[]>([]);
  total = signal(0);
  page = signal(1);
  pageSize = 50;
  rows = Array(8)
    .fill(0)
    .map((_, i) => i);

  orderBy = signal('-last_seen');
  sortDir = signal<Record<string, 'asc' | 'desc'>>({});
  selectedIds = signal<Set<string>>(new Set());
  selectedDevice = signal<any>(null);
  editingDevice = signal<any>(null);

  // Add Device modal state
  showAddModal = signal(false);
  addLoading = signal(false);
  createdDevice = signal<any>(null);   // holds the newly created device to display its api_key
  addForm: { hostname: string; ip_address: string; os_family: string; environment: 'production' | 'staging' | 'development'; agent_version: string } = {
    hostname: '',
    ip_address: '',
    os_family: 'linux',
    environment: 'production',
    agent_version: '',
  };

  // Bulk tag modal state
  showTagModal = signal(false);
  tagInput = '';

  // Bulk group modal state
  showGroupModal = signal(false);
  groupInput = '';

  searchTerm = '';
  activeStatus = '';
  activeOs = '';
  activeEnv = '';

  private search$ = new Subject<string>();

  statusOptions = [
    { label: 'UI.u_all', value: '' },
    { label: 'UI.u_online', value: 'online' },
    { label: 'UI.u_offline', value: 'offline' },
    { label: 'UI.u_maintenance', value: 'maintenance' },
  ];

  osOptions = ['All', 'Linux', 'Windows', 'macOS'];
  envOptions = ['All', 'Production', 'Staging'];

  totalPages() {
    return Math.ceil(this.total() / this.pageSize);
  }

  allSelected() {
    const ids = this.devices().map((d) => d.id);
    return ids.length > 0 && ids.every((id) => this.selectedIds().has(id));
  }

  pageNumbers(): number[] {
    const total = this.totalPages();
    const current = this.page();
    const pages: number[] = [];
    for (let i = Math.max(1, current - 2); i <= Math.min(total, current + 2); i++) pages.push(i);
    return pages;
  }

  getOsIcon(os: string): string {
    if (!os) return '\u{1F4BB}';
    const l = os.toLowerCase();
    if (l.includes('linux')) return '\u{1F427}';
    if (l.includes('windows')) return '\u{1F5A5}';
    if (l.includes('mac')) return '\u{1F34E}';
    return '\u{1F4BB}';
  }

  getComplianceColor(rate: number): string {
    if (rate >= 90) return 'bg-success';
    if (rate >= 70) return 'bg-warning';
    return 'bg-danger';
  }

  ngOnInit() {
    this.loadDevices();
    this.search$.pipe(debounceTime(350)).subscribe(() => {
      this.page.set(1);
      this.loadDevices();
    });

    this.wsSub = this.ws.messages$.subscribe(msg => {
      if (['status_change', 'agent_online', 'agent_offline'].includes(msg.event)) {
        const { device_id, status } = msg.payload;
        const newStatus = msg.event === 'agent_online' ? 'online' : (msg.event === 'agent_offline' ? 'offline' : status);
        
        this.devices.update(list => list.map(d => {
          if (d.id === device_id) {
            return { ...d, status: newStatus, last_seen: new Date().toISOString() };
          }
          return d;
        }));
      }
    });
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
  }

  loadDevices() {
    this.loading.set(true);
    const params: any = { page: this.page(), page_size: this.pageSize, ordering: this.orderBy() };
    if (this.searchTerm) params.search = this.searchTerm;
    if (this.activeStatus) params.status = this.activeStatus;
    if (this.activeOs) params.os_family = this.activeOs;
    if (this.activeEnv) params.environment = this.activeEnv;
    this.deviceSvc.getDevices(params).subscribe({
      next: (r) => {
        this.devices.set(r.results ?? []);
        this.total.set(r.count ?? 0);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  refreshDevices() {
    this.loadDevices();
  }
  onSearch(v: string) {
    this.search$.next(v);
  }
  clearSearch() {
    this.searchTerm = '';
    this.search$.next('');
  }
  setStatus(v: string) {
    this.activeStatus = v;
    this.page.set(1);
    this.loadDevices();
  }
  setOs(v: string) {
    this.activeOs = v === 'All' ? '' : v.toLowerCase();
    this.page.set(1);
    this.loadDevices();
  }
  setEnv(v: string) {
    this.activeEnv = v === 'All' ? '' : v.toLowerCase();
    this.page.set(1);
    this.loadDevices();
  }
  setPage(p: number) {
    this.page.set(p);
    this.loadDevices();
  }

  sort(col: string) {
    const current = this.sortDir()[col];
    const next = current === 'asc' ? 'desc' : 'asc';
    this.sortDir.update((d) => ({ ...d, [col]: next }));
    this.orderBy.set((next === 'desc' ? '-' : '') + col);
    this.loadDevices();
  }

  sortIcon(col: string): string {
    const dir = this.sortDir()[col];
    if (!dir) return '\u2195';
    return dir === 'asc' ? '\u2191' : '\u2193';
  }

  toggleSelect(id: string) {
    this.selectedIds.update((set) => {
      const next = new Set(set);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  toggleAll(e: Event) {
    const checked = (e.target as HTMLInputElement).checked;
    this.selectedIds.set(checked ? new Set(this.devices().map((d) => d.id)) : new Set());
  }

  clearSelection() {
    this.selectedIds.set(new Set());
  }

  bulkScan() {
    const ids = Array.from(this.selectedIds());
    ids.forEach((id) => this.deviceSvc.scanTarget(id).subscribe());
    this.ns.success('Scan Triggered', `Scan initiated for ${ids.length} device(s).`);
    this.clearSelection();
  }

  openDetail(device: any) {
    this.selectedDevice.set(device);
  }

  handleEdit(device: any) {
    this.editingDevice.set(device);
  }

  handleSaved(updated: any) {
    this.devices.update(list => list.map(d => d.id === updated.id ? updated : d));
    this.selectedDevice.set(updated);
  }

  handleDeleted(id: string) {
    this.devices.update(list => list.filter(d => d.id !== id));
    this.selectedIds.update(s => { const n = new Set(s); n.delete(id); return n; });
  }

  openAddModal() {
    this.addForm = { hostname: '', ip_address: '', os_family: 'linux', environment: 'production' as const, agent_version: '' };
    this.createdDevice.set(null);
    this.showAddModal.set(true);
  }

  closeAddModal() {
    this.showAddModal.set(false);
    this.createdDevice.set(null);
  }

  submitAddDevice() {
    if (!this.addForm.hostname.trim() || !this.addForm.ip_address.trim()) {
      this.ns.error('Validation Error', 'Hostname and IP address are required.');
      return;
    }
    this.addLoading.set(true);
    this.deviceSvc.createDevice(this.addForm).subscribe({
      next: (device: any) => {
        this.addLoading.set(false);
        this.createdDevice.set(device);   // show the api_key to the user
        this.loadDevices();
      },
      error: (err: any) => {
        this.addLoading.set(false);
        const detail = err?.error?.detail ?? err?.error?.hostname?.[0] ?? 'Failed to add device.';
        this.ns.error('Add Device Failed', typeof detail === 'string' ? detail : JSON.stringify(detail));
      },
    });
  }

  copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      this.ns.success('Copied', 'API key copied to clipboard.');
    });
  }

  bulkTag() {
    const tags = this.tagInput.split(',').map(t => t.trim()).filter(Boolean);
    if (!tags.length) { this.ns.error('Error', 'Enter at least one tag.'); return; }
    const ids = Array.from(this.selectedIds());
    this.deviceSvc.bulkTag(ids, tags, 'add').subscribe({
      next: () => {
        this.ns.success('Tags Applied', `Tags added to ${ids.length} device(s).`);
        this.showTagModal.set(false);
        this.tagInput = '';
        this.clearSelection();
        this.loadDevices();
      },
      error: () => this.ns.error('Error', 'Bulk tag failed.'),
    });
  }

  bulkGroup() {
    const groupId = this.groupInput.trim();
    if (!groupId) { this.ns.error('Error', 'Enter a group ID.'); return; }
    const ids = Array.from(this.selectedIds());
    this.deviceSvc.bulkGroup(ids, groupId).subscribe({
      next: () => {
        this.ns.success('Group Assigned', `${ids.length} device(s) added to group.`);
        this.showGroupModal.set(false);
        this.groupInput = '';
        this.clearSelection();
      },
      error: () => this.ns.error('Error', 'Bulk group assignment failed.'),
    });
  }
}
