import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { DeploymentService } from '../../../core/services/deployment.service';
import { AuthService } from '../../../core/auth/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';

@Component({
  selector: 'app-deployment-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    TranslateModule,
    StatusBadgeComponent,
    LoadingSkeletonComponent,
    EmptyStateComponent,
    RelativeTimePipe,
  ],
  templateUrl: './deployment-list.component.html',
  styleUrl: './deployment-list.component.scss',
})
export class DeploymentListComponent implements OnInit {
  private deploySvc = inject(DeploymentService);
  private auth = inject(AuthService);
  private ns = inject(NotificationService);

  isAdmin = this.auth.isAdmin;

  loading = signal(true);
  deployments = signal<any[]>([]);
  total = signal(0);
  page = signal(1);
  pageSize = 20;
  activeFilter = '';

  statusFilters = [
    { label: 'All', value: '' },
    { label: 'Draft', value: 'draft' },
    { label: 'Scheduled', value: 'scheduled' },
    { label: 'In Progress', value: 'in_progress' },
    { label: 'Completed', value: 'completed' },
    { label: 'Failed', value: 'failed' },
  ];

  ngOnInit() {
    this.load();
  }

  load() {
    this.loading.set(true);
    const params: any = { page: this.page(), page_size: 20 };
    if (this.activeFilter) params.status = this.activeFilter;
    this.deploySvc.getDeployments(params).subscribe({
      next: (r: any) => {
        this.deployments.set(r.results ?? []);
        this.total.set(r.count ?? 0);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  setFilter(v: string) {
    this.activeFilter = v;
    this.page.set(1);
    this.load();
  }
  setPage(p: number) {
    this.page.set(p);
    this.load();
  }
  totalPages() {
    return Math.ceil(this.total() / 20);
  }

  getProgress(d: any): number {
    if (!d.target_count) return 0;
    return Math.round(((d.success_count ?? 0) / d.target_count) * 100);
  }

  approveDeployment(d: any, event: Event) {
    event.stopPropagation();
    this.deploySvc.approve(d.id).subscribe({
      next: () => {
        this.ns.success('Approved', `Deployment "${d.name}" approved and scheduled.`);
        this.load();
      },
      error: (err: any) => {
        const msg = err?.error?.error || 'Failed to approve deployment.';
        this.ns.error('Error', msg);
      },
    });
  }

  executeDeployment(d: any, event: Event) {
    event.stopPropagation();
    this.deploySvc.execute(d.id).subscribe({
      next: () => {
        this.ns.success('Started', `Deployment "${d.name}" execution started.`);
        this.load();
      },
      error: (err: any) => {
        const msg = err?.error?.error || 'Failed to execute deployment.';
        this.ns.error('Error', msg);
      },
    });
  }
}
