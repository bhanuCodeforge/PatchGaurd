import { Component, OnInit, OnDestroy, signal, inject, computed, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { TranslateModule } from '@ngx-translate/core';
import { ScrollingModule, CdkVirtualScrollViewport } from '@angular/cdk/scrolling';
import { DeploymentService } from '../../../core/services/deployment.service';
import { WebsocketService } from '../../../core/services/websocket.service';
import { NotificationService } from '../../../core/services/notification.service';

/** Maximum events kept in the live log (virtual-scrolled for performance). */
const MAX_LOG_EVENTS = 5000;

@Component({
  selector: 'app-deployment-live',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslateModule, ScrollingModule],
  templateUrl: './deployment-live.component.html',
  styleUrl: './deployment-live.component.scss',
})
export class DeploymentLiveComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild(CdkVirtualScrollViewport) viewport?: CdkVirtualScrollViewport;

  private route = inject(ActivatedRoute);
  private deploySvc = inject(DeploymentService);
  private wsSvc = inject(WebsocketService);
  private ns = inject(NotificationService);

  loading = signal(true);
  deployment = signal<any>(null);
  targets = signal<any[]>([]);

  /**
   * Event log — kept as a signal array for CDK virtual scroll.
   * Limited to MAX_LOG_EVENTS to prevent unbounded memory growth.
   */
  events = signal<{ ts: string; message: string; level: string }[]>([]);

  /** Whether the log view is pinned to the bottom (auto-scroll). */
  autoscroll = signal(true);

  stats = signal({ total: 0, success: 0, failed: 0, pending: 0, in_progress: 0 });

  /** Elapsed time as MM:SS string, updated every second. */
  elapsedSeconds = signal(0);
  elapsed = computed(() => {
    const s = this.elapsedSeconds();
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  });

  failureRate = computed(() => {
    const t = this.stats().total;
    if (t === 0) return 0;
    return +((this.stats().failed / t) * 100).toFixed(1);
  });

  waves = computed(() => this.deployment()?.wave_summary || []);

  private subs: Subscription[] = [];
  deploymentId = '';
  private _shouldScroll = false;

  progressPct() {
    return this.deployment()?.progress_percentage || 0;
  }

  heatColor(status: string) {
    const m: Record<string, string> = {
      completed:   '#10b981',
      success:     '#10b981',
      failed:      '#ef4444',
      in_progress: '#3b82f6',
      installing:  '#3b82f6',
      queued:      '#1e293b',
      skipped:     '#4b5563',
    };
    return m[status] ?? '#1e293b';
  }

  /** Track by function for CDK virtual scroll — avoids full re-render on push. */
  trackEvent(_idx: number, ev: { ts: string; message: string }) {
    return `${ev.ts}-${ev.message.slice(0, 20)}`;
  }

  ngOnInit() {
    this.deploymentId = this.route.snapshot.paramMap.get('id') ?? '';
    this.load();

    // Slower polling for full object consistency
    const poll = interval(15_000)
      .pipe(switchMap(() => this.deploySvc.getDeploymentById(this.deploymentId)))
      .subscribe((d) => this.deployment.set(d));
    this.subs.push(poll);

    // Elapsed time ticker
    const ticker = interval(1000).subscribe(() => {
      const d = this.deployment();
      if (!d?.started_at) {
        this.elapsedSeconds.update((v) => v + 1);
        return;
      }
      const diff = Math.floor((Date.now() - new Date(d.started_at).getTime()) / 1000);
      this.elapsedSeconds.set(Math.max(0, diff));
    });
    this.subs.push(ticker);

    // Real-time updates via WebSocket
    const ws = this.wsSvc.messages$.subscribe((msg: any) => {
      if (msg?.payload?.deployment_id === this.deploymentId || msg?.deployment_id === this.deploymentId) {
        this.handleWsMessage(msg);
      }
    });
    this.subs.push(ws);

    // Load persistent deployment events from backend (Task 11.5)
    this.loadDeploymentEvents();
  }

  ngAfterViewChecked() {
    if (this._shouldScroll && this.autoscroll() && this.viewport) {
      this.viewport.scrollToIndex(this.events().length - 1, 'smooth');
      this._shouldScroll = false;
    }
  }

  private handleWsMessage(msg: any) {
    const payload = msg?.payload || msg;
    this.appendEvent(
      payload.message || payload.text || `WS: ${msg.channel || 'update'}`,
      payload.level || 'info',
    );

    // Refresh full data on significant changes
    if (
      msg.type === 'deployment_target_update' ||
      msg.type === 'deployment_status' ||
      msg.type === 'deployment_wave_advance' ||
      payload.status
    ) {
      this.load();
    }
  }

  private appendEvent(message: string, level = 'info') {
    this.events.update((ev) => {
      const updated = [
        ...ev,
        { ts: new Date().toISOString(), message, level },
      ];
      // Trim to MAX_LOG_EVENTS — keep most-recent
      return updated.length > MAX_LOG_EVENTS ? updated.slice(-MAX_LOG_EVENTS) : updated;
    });
    this._shouldScroll = true;
  }

  toggleAutoscroll() {
    this.autoscroll.update((v) => !v);
  }

  load() {
    this.deploySvc.getDeploymentById(this.deploymentId).subscribe({
      next: (d) => {
        this.deployment.set(d);
        this.loading.set(false);
        if (d?.started_at) {
          this.elapsedSeconds.set(
            Math.max(0, Math.floor((Date.now() - new Date(d.started_at).getTime()) / 1000)),
          );
        }
        this.loadTargets();
      },
      error: () => this.loading.set(false),
    });
  }

  loadTargets() {
    this.deploySvc.getTargets(this.deploymentId, { page_size: 1000 }).subscribe((r: any) => {
      const list = r.results ?? r;
      this.targets.set(list);

      const s = { total: list.length, success: 0, failed: 0, pending: 0, in_progress: 0 };
      for (const t of list) {
        if (t.status === 'success' || t.status === 'completed') s.success++;
        else if (t.status === 'failed') s.failed++;
        else if (t.status === 'in_progress' || t.status === 'installing') s.in_progress++;
        else s.pending++;
      }
      this.stats.set(s);
    });
  }

  loadDeploymentEvents() {
    // Load persistent events from the backend DeploymentEvent table (Task 11.5)
    this.deploySvc.getDeploymentEvents(this.deploymentId).subscribe({
      next: (resp: any) => {
        const evts = (resp.results ?? resp) as any[];
        if (evts.length > 0 && this.events().length === 0) {
          this.events.set(
            evts.map((e: any) => ({
              ts: e.occurred_at || e.timestamp || new Date().toISOString(),
              message: this.formatEvent(e),
              level: e.event_type === 'failed' ? 'error' : 'info',
            })).reverse(),  // oldest first
          );
        }
      },
      error: () => {/* non-critical: log not available yet */},
    });
  }

  private formatEvent(e: any): string {
    const device = e.device_hostname || e.device_id || 'unknown';
    switch (e.event_type) {
      case 'wave_start':   return `Wave ${e.wave_number} started`;
      case 'wave_done':    return `Wave ${e.wave_number} completed`;
      case 'started':      return `${device}: patching started`;
      case 'completed':    return `${device}: patching completed ✓`;
      case 'failed':       return `${device}: FAILED — ${e.detail?.error_log || 'unknown error'}`;
      case 'skipped':      return `${device}: skipped (preflight failed)`;
      case 'cancelled':    return `Deployment cancelled`;
      default:             return `${e.event_type} — ${device}`;
    }
  }

  pause() {
    this.deploySvc.pause(this.deploymentId).subscribe({
      next: () => { this.ns.success('Paused', 'Deployment execution halted.'); this.load(); },
      error: () => this.ns.error('Error', 'Pause failed.'),
    });
  }

  resume() {
    this.deploySvc.resume(this.deploymentId).subscribe({
      next: () => { this.ns.success('Resumed', 'Deployment execution resumed.'); this.load(); },
      error: () => this.ns.error('Error', 'Resume failed.'),
    });
  }

  cancel() {
    this.deploySvc.cancel(this.deploymentId).subscribe({
      next: () => { this.ns.success('Cancelled', 'Deployment has been stopped.'); this.load(); },
      error: () => this.ns.error('Error', 'Cancel failed.'),
    });
  }

  rollback() {
    this.deploySvc.rollback(this.deploymentId).subscribe({
      next: () => { this.ns.success('Rolling Back', 'Patch removal initiated.'); this.load(); },
      error: () => this.ns.error('Error', 'Rollback failed.'),
    });
  }

  ngOnDestroy() {
    this.subs.forEach((s) => s.unsubscribe());
  }
}
