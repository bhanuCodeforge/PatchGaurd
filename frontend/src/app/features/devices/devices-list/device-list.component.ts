import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { debounceTime, Subject } from 'rxjs';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { DeviceDetailComponent } from '../devices-detail/device-detail.component';

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
  ],
  templateUrl: './device-list.component.html',
  styleUrl: './device-list.component.scss',
})
export class DeviceListComponent implements OnInit {
  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);
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

  // Add Device modal state
  showAddModal = signal(false);
  addLoading = signal(false);
  addForm: { hostname: string; ip_address: string; os_family: string; environment: 'production' | 'staging' | 'development'; agent_version: string } = {
    hostname: '',
    ip_address: '',
    os_family: 'linux',
    environment: 'production',
    agent_version: '',
  };

  searchTerm = '';
  activeStatus = '';
  activeOs = '';
  activeEnv = '';

  private search$ = new Subject<string>();

  statusOptions = [
    { label: 'DEVICES.ALL', value: '' },
    { label: 'DEVICES.ONLINE', value: 'online' },
    { label: 'DEVICES.OFFLINE', value: 'offline' },
    { label: 'DEVICES.MAINTENANCE', value: 'maintenance' },
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

  openAddModal() {
    this.addForm = { hostname: '', ip_address: '', os_family: 'linux', environment: 'production' as const, agent_version: '' };
    this.showAddModal.set(true);
  }

  closeAddModal() {
    this.showAddModal.set(false);
  }

  submitAddDevice() {
    if (!this.addForm.hostname.trim() || !this.addForm.ip_address.trim()) {
      this.ns.error('Validation Error', 'Hostname and IP address are required.');
      return;
    }
    this.addLoading.set(true);
    this.deviceSvc.createDevice(this.addForm).subscribe({
      next: () => {
        this.addLoading.set(false);
        this.showAddModal.set(false);
        this.ns.success('Device Added', `${this.addForm.hostname} was registered successfully.`);
        this.loadDevices();
      },
      error: (err: any) => {
        this.addLoading.set(false);
        const detail = err?.error?.detail ?? err?.error?.hostname?.[0] ?? 'Failed to add device.';
        this.ns.error('Add Device Failed', typeof detail === 'string' ? detail : JSON.stringify(detail));
      },
    });
  }
}
