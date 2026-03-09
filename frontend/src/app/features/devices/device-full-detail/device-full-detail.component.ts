import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';
import { Device } from '../../../core/models/types';
import { WebsocketService } from '../../../core/services/websocket.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog.component';
import { Subscription } from 'rxjs';

import { trigger, transition, style, animate, query, stagger } from '@angular/animations';

@Component({
  selector: 'app-device-full-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    TranslateModule,
    StatusBadgeComponent,
    LoadingSkeletonComponent,
    RelativeTimePipe,
    ConfirmDialogComponent,
  ],
  templateUrl: './device-full-detail.component.html',
  styleUrl: './device-full-detail.component.scss',
  animations: [
    trigger('listAnimation', [
      transition('* <=> *', [
        query(
          ':enter',
          [
            style({ opacity: 0, transform: 'translateY(15px)' }),
            stagger('50ms', [
              animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
            ]),
          ],
          { optional: true },
        ),
      ]),
    ]),
    trigger('tabChange', [
      transition(':enter', [
        style({ opacity: 0, scale: 0.98 }),
        animate('200ms ease-out', style({ opacity: 1, scale: 1 })),
      ]),
    ]),
  ],
})
export class DeviceFullDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);
  private ws = inject(WebsocketService);
  private translate = inject(TranslateService);
  private wsSub?: Subscription;

  loading = signal(true);
  device = signal<Device | null>(null);
  patches = signal<any[]>([]);
  availablePatches = signal<any[]>([]);
  installedPatches = signal<any[]>([]);
  failedPatches = signal<any[]>([]);
  recentPatches = signal<any[]>([]);
  deployments = signal<any[]>([]);
  systemInfo = signal<any>(null);
  installedApps = signal<any[]>([]);
  isEditing = signal(false);
  activeTab = signal('overview');
  patchSubTab = signal<'available' | 'installed' | 'failed' | 'recent'>('available');
  inventoryTab = signal('system');
  appSearch = signal('');
  editData = { hostname: '', description: '' };
  configData = { log_level: 'info', heartbeat_interval: 60 };
  showRebootDialog = signal(false);
  showDeleteDialog = signal(false);
  activityLog = signal<any[]>([]);
  activityLoading = signal(false);
  appsLoading = signal(false);
  systemInfoLoading = signal(false);
  patchesLoading = signal(false);

  patchCounts = computed(() => {
    const ps = this.patches();
    return {
      total: ps.length,
      installed: ps.filter((p) => p.state === 'installed').length,
      pending: ps.filter((p) => p.state === 'pending' || p.state === 'missing').length,
      failed: ps.filter((p) => p.state === 'failed').length,
    };
  });

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadDevice(id);
      this.setupWebsocket(id);
    } else {
      this.router.navigate(['/devices']);
    }
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
  }

  setupWebsocket(id: string) {
    this.wsSub = this.ws.messages$.subscribe((msg) => {
      const current = this.device();
      if (!current || msg.payload?.device_id !== id) return;

      if (msg.event === 'agent_heartbeat') {
        this.device.update((d) =>
          d
            ? {
                ...d,
                last_seen: new Date().toISOString(),
                metadata: { ...d.metadata, ...msg.payload },
              }
            : null,
        );
      } else if (msg.event === 'agent_inventory_info') {
        this.device.update((d) => (d ? { ...d, inventory_data: msg.payload.inventory } : null));
      } else if (msg.event === 'status_change') {
        this.device.update((d) => (d ? { ...d, status: msg.payload.status } : null));
      } else if (msg.event === 'scan_results') {
        this.ns.success('Scan Complete', `New patches discovered for ${current.hostname}`);
        this.loadPatches(id);
      }
    });
  }

  loadDevice(id: string) {
    this.loading.set(true);
    this.deviceSvc.getDeviceById(id).subscribe({
      next: (d) => {
        this.device.set(d);
        this.editData = { hostname: d.hostname, description: d.description || '' };
        this.configData = {
          log_level: d.metadata?.log_level || 'info',
          heartbeat_interval: d.metadata?.heartbeat_interval || 60,
        };
        this.loadAllPatches(id);
        this.loadDeployments(id);
        this.loadSystemInfo(id);
        this.loadInstalledApps(id);
        this.loading.set(false);
      },
      error: () => {
        this.ns.error('Error', 'Failed to load device details.');
        this.router.navigate(['/devices']);
      },
    });
  }

  loadAllPatches(id: string) {
    this.patchesLoading.set(true);
    // Load all patches (no pagination limit for overview)
    this.deviceSvc.getDevicePatches(id, { page_size: 500 }).subscribe({
      next: (r) => {
        const all = r.results || [];
        this.patches.set(all);
        this.availablePatches.set(
          all.filter((p: any) => p.state === 'missing' || p.state === 'pending'),
        );
        this.installedPatches.set(all.filter((p: any) => p.state === 'installed'));
        this.failedPatches.set(all.filter((p: any) => p.state === 'failed'));
        // Recently updated = patches with last_attempt or installed_at, sorted by most recent
        const recent = [...all]
          .filter((p: any) => p.installed_at || p.last_attempt)
          .sort((a: any, b: any) => {
            const da = new Date(a.installed_at || a.last_attempt).getTime();
            const db = new Date(b.installed_at || b.last_attempt).getTime();
            return db - da;
          })
          .slice(0, 20);
        this.recentPatches.set(recent);
        this.patchesLoading.set(false);
      },
      error: () => this.patchesLoading.set(false),
    });
  }

  loadPatches(id: string) {
    this.loadAllPatches(id);
  }

  loadDeployments(id: string) {
    this.deviceSvc.getDeviceDeployments(id).subscribe((dls) => this.deployments.set(dls || []));
  }

  loadSystemInfo(id: string) {
    this.systemInfoLoading.set(true);
    this.deviceSvc.getSystemInfo(id).subscribe({
      next: (info) => {
        this.systemInfo.set(info);
        this.systemInfoLoading.set(false);
      },
      error: () => this.systemInfoLoading.set(false),
    });
  }

  loadInstalledApps(id: string, search: string = '') {
    this.appsLoading.set(true);
    const params: any = {};
    if (search) params.search = search;
    this.deviceSvc.getInstalledApps(id, params).subscribe({
      next: (r) => {
        this.installedApps.set(r.results || []);
        this.appsLoading.set(false);
      },
      error: () => this.appsLoading.set(false),
    });
  }

  searchApps(term: string) {
    this.appSearch.set(term);
    const d = this.device();
    if (d) this.loadInstalledApps(d.id, term);
  }

  loadActivityLog(id: string) {
    this.activityLoading.set(true);
    this.deviceSvc.getDeviceActivity(id).subscribe({
      next: (r) => {
        this.activityLog.set(r.results || r || []);
        this.activityLoading.set(false);
      },
      error: () => this.activityLoading.set(false),
    });
  }

  scan() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc
      .scanTarget(d.id)
      .subscribe(() => this.ns.success('Scan Started', `Remote scan initiated for ${d.hostname}`));
  }

  reboot() {
    this.showRebootDialog.set(true);
  }

  confirmReboot() {
    const d = this.device();
    if (!d) return;

    this.showRebootDialog.set(false);
    this.deviceSvc.rebootTarget(d.id).subscribe(() => {
      const title = this.translate.instant('UI.u_reboot_title');
      const msg = this.translate.instant('MSG.m_reboot_confirm', { hostname: d.hostname });
      this.ns.info(title, msg);
    });
  }

  deleteDevice() {
    this.showDeleteDialog.set(true);
  }

  confirmDelete() {
    const d = this.device();
    if (!d) return;

    this.showDeleteDialog.set(false);
    this.deviceSvc.deleteDevice(d.id).subscribe({
      next: () => {
        this.ns.success('Deleted', `Device ${d.hostname} has been removed.`);
        this.router.navigate(['/devices']);
      },
    });
  }

  toggleEdit() {
    this.isEditing.set(!this.isEditing());
  }

  save() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.updateDevice(d.id, this.editData).subscribe({
      next: (updated) => {
        this.device.set(updated);
        this.isEditing.set(false);
        this.ns.success('Updated', 'Device properties updated.');
      },
      error: () => this.ns.error('Error', 'Failed to update device.'),
    });
  }

  pushConfig() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.updateAgentConfig(d.id, this.configData).subscribe({
      next: () => {
        this.ns.success('Config Sent', 'Agent configuration update command published.');
      },
      error: () => this.ns.error('Error', 'Failed to send config update.'),
    });
  }

  get filteredApps() {
    return this.installedApps();
  }

  formatBytes(bytes: number): string {
    if (!bytes) return '—';
    const gb = bytes / 1073741824;
    if (gb >= 1) return gb.toFixed(gb >= 100 ? 0 : 1) + ' GB';
    const mb = bytes / 1048576;
    return mb.toFixed(0) + ' MB';
  }
}
