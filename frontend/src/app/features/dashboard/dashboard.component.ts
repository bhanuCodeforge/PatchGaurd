import { Component, OnInit, OnDestroy, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { ReportService } from '../../core/services/report.service';
import { DeviceService } from '../../core/services/device.service';
import { DeploymentService } from '../../core/services/deployment.service';
import { PatchService } from '../../core/services/patch.service';
import { WebsocketService } from '../../core/services/websocket.service';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslateModule, LoadingSkeletonComponent, RelativeTimePipe],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit, OnDestroy {
  private reportSvc = inject(ReportService);
  private deviceSvc = inject(DeviceService);
  private deploymentSvc = inject(DeploymentService);
  private patchSvc = inject(PatchService);
  private wsSvc = inject(WebsocketService);

  Math = Math;
  loading = signal(true);
  devicesLoading = signal(true);
  deployLoading = signal(true);

  stats = signal<any>(null);
  recentDevices = signal<any[]>([]);
  activeDeployments = signal<any[]>([]);
  criticalPatches = signal<any[]>([]);
  liveEvents = signal<any[]>([]);

  complianceRate = computed(() => {
    const s = this.stats();
    if (!s) return 87;
    if (s.compliance_rate != null) return Math.round(s.compliance_rate);
    const total = s.total_devices || 1;
    const ok = s.compliant_devices ?? s.online_devices ?? 0;
    return Math.round((ok / total) * 100);
  });

  onlinePercent = computed(() => {
    const s = this.stats();
    if (!s) return 0;
    return Math.round(((s.online_devices ?? 0) / (s.total_devices || 1)) * 100);
  });

  osBars = [
    { icon: '\u{1F427}', name: 'Linux',   count: 0, pct: 0, color: 'bg-primary' },
    { icon: '\u{1F5A5}', name: 'Windows', count: 0, pct: 0, color: 'bg-info' },
    { icon: '\u{1F34E}', name: 'macOS',   count: 0, pct: 0, color: 'bg-secondary' },
  ];

  private subs: Subscription[] = [];
  private refreshTimer?: ReturnType<typeof setInterval>;

  ngOnInit() {
    this.loadAll();
    this.refreshTimer = setInterval(() => this.loadStats(), 30000);
    this.subs.push(
      this.wsSvc.messages$.subscribe((msg) => {
        const now = new Date().toLocaleTimeString();
        let entry: any = null;
        if (msg.event === 'deployment_progress') {
          entry = {
            level: 'info',
            type: 'DEPLOY_PROGRESS',
            message: `Deployment ${msg.payload?.status} \u2014 ${msg.payload?.progress_percentage ?? 0}%`,
            time: now,
          };
          this.loadDeployments();
        } else if (msg.event === 'device_status') {
          entry = {
            level: msg.payload?.status === 'offline' ? 'warning' : 'info',
            type: 'DEVICE_STATUS',
            message: `${msg.payload?.hostname} \u2192 ${msg.payload?.status}`,
            time: now,
          };
        } else if (msg.event === 'notification') {
          entry = {
            level: msg.payload?.level || 'info',
            type: 'NOTIFICATION',
            message: msg.payload?.message,
            time: now,
          };
        }
        if (entry) this.liveEvents.update((e) => [entry, ...e].slice(0, 50));
      }),
    );
  }

  ngOnDestroy() {
    this.subs.forEach((s) => s.unsubscribe());
    if (this.refreshTimer) clearInterval(this.refreshTimer);
  }

  private loadAll() {
    this.loadStats();
    this.loadDevices();
    this.loadDeployments();
    this.loadCriticalPatches();
  }

  private loadStats() {
    this.reportSvc.getDashboardStats().subscribe({
      next: (s) => {
        this.stats.set(s);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private loadDevices() {
    this.deviceSvc.getDevices({ page_size: 10 }).subscribe({
      next: (r) => {
        this.recentDevices.set(r.results ?? []);
        this.devicesLoading.set(false);
        this.updateOsBreakdown();
      },
      error: () => this.devicesLoading.set(false),
    });
  }

  private updateOsBreakdown() {
    const s = this.stats();
    if (!s || !s.by_os) return;

    const byOs = s.by_os;
    const total = s.total_devices || 1;

    const linux = byOs['linux'] || 0;
    const win = byOs['windows'] || 0;
    const mac = byOs['macos'] || 0;

    this.osBars[0].count = linux;
    this.osBars[0].pct = Math.round((linux / total) * 100);
    this.osBars[1].count = win;
    this.osBars[1].pct = Math.round((win / total) * 100);
    this.osBars[2].count = mac;
    this.osBars[2].pct = Math.round((mac / total) * 100);
  }

  private loadDeployments() {
    this.deploymentSvc
      .getDeployments({ status: 'in_progress,scheduled,paused', page_size: 5 })
      .subscribe({
        next: (r) => {
          this.activeDeployments.set(r.results ?? []);
          this.deployLoading.set(false);
        },
        error: () => this.deployLoading.set(false),
      });
  }

  private loadCriticalPatches() {
    this.patchSvc
      .getPatches({ severity: 'critical', status: 'approved,imported', page_size: 6 })
      .subscribe({
        next: (r) => this.criticalPatches.set(r.results ?? []),
        error: () => {},
      });
  }
}
