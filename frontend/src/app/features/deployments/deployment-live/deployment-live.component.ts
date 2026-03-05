import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { TranslateModule } from '@ngx-translate/core';
import { DeploymentService } from '../../../core/services/deployment.service';
import { WebsocketService } from '../../../core/services/websocket.service';
import { NotificationService } from '../../../core/services/notification.service';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';

@Component({
  selector: 'app-deployment-live',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslateModule, RelativeTimePipe, StatusBadgeComponent],
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
  stats = signal({ total: 0, success: 0, failed: 0, pending: 0 });

  private subs: Subscription[] = [];
  deploymentId = '';

  progressPct() {
    const s = this.stats();
    return s.total ? Math.round(((s.success + s.failed) / s.total) * 100) : 0;
  }
  successPct() {
    const s = this.stats();
    return s.total ? (s.success / s.total) * 100 : 0;
  }
  failedPct() {
    const s = this.stats();
    return s.total ? (s.failed / s.total) * 100 : 0;
  }

  heatColor(status: string) {
    const m: Record<string, string> = {
      success: '#22c55e',
      failed: '#ef4444',
      in_progress: '#3b82f6',
      pending: '#374151',
      skipped: '#6b7280',
    };
    return m[status] ?? '#374151';
  }

  ngOnInit() {
    this.deploymentId = this.route.snapshot.paramMap.get('id') ?? '';
    this.load();
    const poll = interval(10000)
      .pipe(switchMap(() => this.deploySvc.getDeploymentById(this.deploymentId)))
      .subscribe((d) => {
        this.deployment.set(d);
        if (d.status !== 'in_progress') this.loadTargets();
      });
    this.subs.push(poll);
    const ws = this.wsSvc.messages$.subscribe((msg: any) => {
      if (msg?.deployment_id === this.deploymentId) {
        this.events.update((ev) =>
          [
            {
              ts: new Date().toISOString(),
              message: msg.message ?? JSON.stringify(msg),
              level: msg.level ?? 'info',
            },
            ...ev,
          ].slice(0, 200),
        );
        if (msg.type === 'deployment_target_update') this.loadTargets();
        if (msg.type === 'deployment_status') this.load();
      }
    });
    this.subs.push(ws);
  }

  load() {
    this.deploySvc.getDeploymentById(this.deploymentId).subscribe({
      next: (d) => {
        this.deployment.set(d);
        this.loading.set(false);
        this.loadTargets();
      },
      error: () => this.loading.set(false),
    });
  }

  loadTargets() {
    this.deploySvc.getTargets(this.deploymentId).subscribe((r: any) => {
      const list = r.results ?? r;
      this.targets.set(list);
      const s = { total: list.length, success: 0, failed: 0, pending: 0 };
      for (const t of list) {
        if (t.status === 'success') s.success++;
        else if (t.status === 'failed') s.failed++;
        else s.pending++;
      }
      this.stats.set(s);
    });
  }

  pause() {
    this.deploySvc
      .pause(this.deploymentId)
      .subscribe({ next: () => this.load(), error: () => this.ns.error('Error', 'Pause failed.') });
  }
  cancel() {
    this.deploySvc
      .cancel(this.deploymentId)
      .subscribe({
        next: () => this.load(),
        error: () => this.ns.error('Error', 'Cancel failed.'),
      });
  }
  rollback() {
    this.deploySvc
      .rollback(this.deploymentId)
      .subscribe({
        next: () => this.load(),
        error: () => this.ns.error('Error', 'Rollback failed.'),
      });
  }
  ngOnDestroy() {
    this.subs.forEach((s) => s.unsubscribe());
  }
}
