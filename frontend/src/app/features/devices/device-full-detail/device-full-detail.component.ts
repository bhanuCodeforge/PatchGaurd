import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';
import { Device } from '../../../core/models/types';
import { WebsocketService } from '../../../core/services/websocket.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { SshTerminalComponent } from '../ssh-terminal/ssh-terminal.component';
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
    SshTerminalComponent,
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
export class DeviceFullDetailComponent implements OnInit, OnDestroy {
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

  // Fast-lane real-time metrics (updated every ~5s via WS)
  liveMetrics = signal<any>(null);

  // Slow-lane section data (loaded on demand per tab)
  slowLaneSummary = signal<any>(null);
  slowSectionData = signal<any>(null);
  slowSectionLoading = signal(false);
  slowActiveSection = signal('');

  // Installer download
  installerDownloading = signal(false);

  // Inventory scan
  scanningInventory = signal(false);
  scanningFastLane = signal(false);

  // Alert summary (new)
  alertSummary = signal<any>(null);

  // Timeline events (new)
  timelineEvents = signal<any[]>([]);
  timelineLoading = signal(false);
  timelineFilter = signal<string>('');

  // Agent health (new)
  agentHealth = signal<any>(null);
  agentHealthLoading = signal(false);

  // Lane config (new)
  laneConfigModel: any = {
    fast_lane: {
      interval: 5,
      concurrency: 2,
      rate_limit: 0,
      retry_strategy: 'exponential',
      bandwidth_kbps: 0,
    },
    slow_lane: {
      interval: 900,
      concurrency: 1,
      rate_limit: 0,
      retry_strategy: 'linear',
      bandwidth_kbps: 0,
    },
  };

  // Per-patch install in progress
  installingPatchId = signal<string | null>(null);

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
      // Subscribe to device-specific WS events
      this.ws.send('subscribe_device', { device_id: id });
    } else {
      this.router.navigate(['/devices']);
    }
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
    const d = this.device();
    if (d) {
      this.ws.send('unsubscribe_device', { device_id: d.id });
    }
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
      } else if (msg.event === 'agent_metrics') {
        // Fast-lane: real-time performance metrics (every ~5s)
        this.liveMetrics.set(msg.payload);
        // Also update device metadata for gauge displays
        this.device.update((d) =>
          d
            ? {
                ...d,
                metadata: {
                  ...d.metadata,
                  cpu_usage: msg.payload.cpu_percent,
                  ram_usage: msg.payload.memory_percent,
                  disk_usage: msg.payload.disk_usage_percent,
                  disk_read_bytes_sec: msg.payload.disk_read_bytes_sec,
                  disk_write_bytes_sec: msg.payload.disk_write_bytes_sec,
                  net_sent_bytes_sec: msg.payload.net_sent_bytes_sec,
                  net_recv_bytes_sec: msg.payload.net_recv_bytes_sec,
                  process_count: msg.payload.process_count,
                },
              }
            : null,
        );
      } else if (msg.event === 'agent_slow_lane_data') {
        // Slow-lane: heavy inventory data refreshed (every ~15min)
        this.ns.info('Inventory Updated', `Slow-lane data refreshed for ${current.hostname}`);
        // Reload affected data from backend
        this.loadInstalledApps(id);
        this.loadAllPatches(id);
        this.loadSystemInfo(id);
      } else if (msg.event === 'patch_install_start') {
        // Per-patch install started on agent
        this.installingPatchId.set(msg.payload.patch_id);
      } else if (msg.event === 'patch_install_result') {
        // Per-patch install completed
        this.installingPatchId.set(null);
        const status = msg.payload.status;
        if (status === 'installed') {
          this.ns.success(
            'Patch Installed',
            `Patch installed successfully (${msg.payload.lane} lane, ${msg.payload.duration_ms}ms)`,
          );
        } else {
          this.ns.error('Patch Failed', `Patch installation failed via ${msg.payload.lane} lane`);
        }
        this.loadAllPatches(id);
        this.loadAlertSummary(id);
      } else if (msg.event === 'reboot_complete') {
        this.ns.success('Reboot Complete', `${current.hostname} has rebooted successfully`);
        this.loadDevice(id);
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
        const cfg = (d as any).lane_config || {};
        this.laneConfigModel = {
          fast_lane: {
            ...this.laneConfigModel.fast_lane,
            ...(cfg.fast_lane || {}),
          },
          slow_lane: {
            ...this.laneConfigModel.slow_lane,
            ...(cfg.slow_lane || {}),
          },
        };
        this.loadAllPatches(id);
        this.loadDeployments(id);
        this.loadSystemInfo(id);
        this.loadInstalledApps(id);
        this.loadSlowLaneSummary(id);
        this.loadAlertSummary(id);
        this.loadAgentHealth(id);
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

  loadSlowLaneSummary(id: string) {
    this.deviceSvc.getSlowLaneSection(id).subscribe({
      next: (r) => this.slowLaneSummary.set(r),
      error: () => {},
    });
  }

  loadAlertSummary(id: string) {
    this.deviceSvc.getAlertSummary(id).subscribe({
      next: (r) => this.alertSummary.set(r),
      error: () => {},
    });
  }

  loadTimeline(id: string, eventType?: string) {
    this.timelineLoading.set(true);
    const params: any = { page_size: 50 };
    if (eventType) params.event_type = eventType;
    this.deviceSvc.getTimeline(id, params).subscribe({
      next: (r) => {
        this.timelineEvents.set(r.results || []);
        this.timelineLoading.set(false);
      },
      error: () => this.timelineLoading.set(false),
    });
  }

  loadAgentHealth(id: string) {
    this.agentHealthLoading.set(true);
    this.deviceSvc.getAgentHealth(id).subscribe({
      next: (r) => {
        this.agentHealth.set(r);
        this.agentHealthLoading.set(false);
      },
      error: () => this.agentHealthLoading.set(false),
    });
  }

  installPatch(patchId: string, lane: 'fast' | 'slow' = 'fast') {
    const d = this.device();
    if (!d || this.installingPatchId()) return;
    this.installingPatchId.set(patchId);
    this.deviceSvc.installPatch(d.id, patchId, lane).subscribe({
      next: () => {
        this.ns.info('Install Initiated', `Patch install command sent via ${lane} lane`);
      },
      error: (err) => {
        this.installingPatchId.set(null);
        this.ns.error('Install Failed', err?.error?.error || 'Could not send install command.');
      },
    });
  }

  decommissionDevice() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.decommissionDevice(d.id).subscribe({
      next: () => {
        this.ns.success('Decommissioned', `Device ${d.hostname} has been decommissioned.`);
        this.router.navigate(['/devices']);
      },
      error: (err) => {
        this.ns.error('Error', err?.error?.error || 'Failed to decommission device.');
      },
    });
  }

  selectInventoryTab(deviceId: string) {
    this.activeTab.set('inventory');
    this.loadSlowLaneSummary(deviceId);
    if (!this.slowActiveSection()) {
      this.loadSlowSection('apps');
    }
  }

  loadSlowSection(section: string) {
    const d = this.device();
    if (!d) return;
    this.slowActiveSection.set(section);

    if (section === 'apps') {
      this.loadInstalledApps(d.id, this.appSearch());
      this.slowSectionData.set(null); // Clear raw data for apps view
      return;
    }

    this.slowSectionLoading.set(true);
    this.deviceSvc.getSlowLaneSection(d.id, section).subscribe({
      next: (r) => {
        this.slowSectionData.set(r.data);
        this.slowSectionLoading.set(false);
      },
      error: () => this.slowSectionLoading.set(false),
    });
  }

  scanInventory() {
    const d = this.device();
    if (!d || this.scanningInventory()) return;
    this.scanningInventory.set(true);
    this.deviceSvc.requestSlowLaneScan(d.id).subscribe({
      next: () => {
        this.ns.success(
          'Slow Lane Triggered',
          `Slow-lane inventory scan command sent to ${d.hostname}. Data will refresh automatically.`,
        );
        this.scanningInventory.set(false);
      },
      error: (err) => {
        this.ns.error(
          'Slow Lane Failed',
          err?.error?.error || 'Could not send slow-lane scan command.',
        );
        this.scanningInventory.set(false);
      },
    });
  }

  scanFastLane() {
    const d = this.device();
    if (!d || this.scanningFastLane()) return;
    this.scanningFastLane.set(true);
    this.deviceSvc.requestFastLaneScan(d.id).subscribe({
      next: () => {
        this.ns.success('Fast Lane Triggered', `Fast-lane metrics refresh sent to ${d.hostname}.`);
        this.scanningFastLane.set(false);
      },
      error: (err) => {
        this.ns.error(
          'Fast Lane Failed',
          err?.error?.error || 'Could not trigger fast-lane refresh.',
        );
        this.scanningFastLane.set(false);
      },
    });
  }

  downloadInstaller() {
    const d = this.device();
    if (!d || this.installerDownloading()) return;
    const os = d.os_family || 'linux';
    this.installerDownloading.set(true);
    this.deviceSvc.downloadInstaller(d.id, os).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `patchguard-agent-${os}-${d.hostname}.zip`;
        a.click();
        URL.revokeObjectURL(url);
        this.installerDownloading.set(false);
        this.ns.success('Download Started', `Agent installer for ${d.hostname} (${os})`);
      },
      error: () => {
        this.installerDownloading.set(false);
        this.ns.error('Download Failed', 'Could not download the agent installer.');
      },
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


  updateLaneConfig() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.updateLaneConfig(d.id, this.laneConfigModel).subscribe({
      next: () => {
        this.ns.success('Lane Config Sent', 'Lane configuration pushed to agent.');
      },
      error: () => this.ns.error('Error', 'Failed to update lane configuration.'),
    });
  }

  resetLaneConfig() {
    this.laneConfigModel = {
      fast_lane: {
        interval: 5,
        concurrency: 2,
        rate_limit: 0,
        retry_strategy: 'exponential',
        bandwidth_kbps: 0,
      },
      slow_lane: {
        interval: 900,
        concurrency: 1,
        rate_limit: 0,
        retry_strategy: 'linear',
        bandwidth_kbps: 0,
      },
    };
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

  formatRate(bytesPerSec: number): string {
    if (!bytesPerSec || bytesPerSec < 0) return '0 B/s';
    if (bytesPerSec >= 1073741824) return (bytesPerSec / 1073741824).toFixed(1) + ' GB/s';
    if (bytesPerSec >= 1048576) return (bytesPerSec / 1048576).toFixed(1) + ' MB/s';
    if (bytesPerSec >= 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s';
    return Math.round(bytesPerSec) + ' B/s';
  }

  getTopProcesses(si: any, limit: number = 12): any[] {
    const list = si?.running_processes;
    if (!Array.isArray(list)) return [];
    return [...list]
      .sort((a: any, b: any) => Number(b?.Memory_MB || 0) - Number(a?.Memory_MB || 0))
      .slice(0, limit);
  }

  formatMemoryMB(mb: any): string {
    const value = Number(mb || 0);
    if (!Number.isFinite(value) || value <= 0) return '0 MB';
    if (value >= 1024) return (value / 1024).toFixed(2) + ' GB';
    return value.toFixed(1) + ' MB';
  }

  /* ── Slow-lane helpers ── */
  objectEntries(obj: any): [string, any][] {
    return obj ? Object.entries(obj) : [];
  }
  objectKeys(obj: any): string[] {
    return obj ? Object.keys(obj) : [];
  }
  isArray(v: any): boolean {
    return Array.isArray(v);
  }
  isObject(v: any): boolean {
    return v !== null && typeof v === 'object' && !Array.isArray(v);
  }
  formatSlowValue(v: any): string {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'boolean') return v ? 'Yes' : 'No';
    if (typeof v === 'object') return JSON.stringify(v, null, 2);
    return String(v);
  }
}
