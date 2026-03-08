import { Component, OnInit, OnDestroy, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { TranslateModule } from '@ngx-translate/core';
import { DeploymentService } from '../../../core/services/deployment.service';
import { WebsocketService } from '../../../core/services/websocket.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-deployment-live',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslateModule],
  templateUrl: './deployment-live.component.html',
  styleUrl: './deployment-live.component.scss',
})
export class DeploymentLiveComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private deploySvc = inject(DeploymentService);
  private wsSvc = inject(WebsocketService);
  private ns = inject(NotificationService);

  loading = signal(true);
  deployment = signal<any>(null);
  targets = signal<any[]>([]);
  events = signal<{ ts: string; message: string; level: string }[]>([]);
  stats = signal({ total: 0, success: 0, failed: 0, pending: 0, in_progress: 0 });

  /** Elapsed time as MM:SS string, updated every second. */
  elapsedSeconds = signal(0);
  elapsed = computed(() => {
    const s = this.elapsedSeconds();
    const m = Math.floor(s / 60)
      .toString()
      .padStart(2, '0');
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

  progressPct() {
    return this.deployment()?.progress_percentage || 0;
  }

  heatColor(status: string) {
    const m: Record<string, string> = {
      completed: '#10b981',
      success: '#10b981',
      failed: '#ef4444',
      in_progress: '#3b82f6',
      installing: '#3b82f6',
      queued: '#1e293b',
      skipped: '#4b5563',
    };
    return m[status] ?? '#1e293b';
  }

  ngOnInit() {
    this.deploymentId = this.route.snapshot.paramMap.get('id') ?? '';
    this.load();

    // Slower polling for full object consistency
    const poll = interval(15000)
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
      if (msg?.deployment_id === this.deploymentId) {
        this.handleWsMessage(msg);
      }
    });
    this.subs.push(ws);
  }

  private handleWsMessage(msg: any) {
    // Add to event log
    this.events.update((ev) =>
      [
        {
          ts: new Date().toISOString(),
          message: msg.message || msg.text || 'Process update received',
          level: msg.level || 'info',
        },
        ...ev,
      ].slice(0, 100),
    );

    // Refresh data on significant changes
    if (
      msg.type === 'deployment_target_update' ||
      msg.type === 'deployment_status' ||
      msg.type === 'deployment_wave_advance'
    ) {
      this.load();
    }
  }

  load() {
    this.deploySvc.getDeploymentById(this.deploymentId).subscribe({
      next: (d) => {
        this.deployment.set(d);
        this.loading.set(false);
        // Seed elapsed from started_at on first load
        if (d?.started_at) {
          this.elapsedSeconds.set(
            Math.max(0, Math.floor((Date.now() - new Date(d.started_at).getTime()) / 1000)),
          );
        }
        // Seed events from deployment log if available
        if (d?.events?.length && this.events().length === 0) {
          this.events.set(
            d.events.map((e: any) => ({
              ts: e.timestamp || new Date().toISOString(),
              message: e.message || e.text || '',
              level: e.level || 'info',
            })),
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

  pause() {
    this.deploySvc.pause(this.deploymentId).subscribe({
      next: () => {
        this.ns.success('Paused', 'Deployment execution halted.');
        this.load();
      },
      error: () => this.ns.error('Error', 'Pause failed.'),
    });
  }

  resume() {
    this.deploySvc.resume(this.deploymentId).subscribe({
      next: () => {
        this.ns.success('Resumed', 'Deployment execution resumed.');
        this.load();
      },
      error: () => this.ns.error('Error', 'Resume failed.'),
    });
  }

  cancel() {
    this.deploySvc.cancel(this.deploymentId).subscribe({
      next: () => {
        this.ns.success('Cancelled', 'Deployment has been stopped.');
        this.load();
      },
      error: () => this.ns.error('Error', 'Cancel failed.'),
    });
  }

  rollback() {
    this.deploySvc.rollback(this.deploymentId).subscribe({
      next: () => {
        this.ns.success('Rolling Back', 'Patch removal initiated.');
        this.load();
      },
      error: () => this.ns.error('Error', 'Rollback failed.'),
    });
  }

  ngOnDestroy() {
    this.subs.forEach((s) => s.unsubscribe());
  }
}
