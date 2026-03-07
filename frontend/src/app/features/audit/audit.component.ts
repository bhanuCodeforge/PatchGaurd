import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { AuditService, AuditLog } from '../../core/services/audit.service';

@Component({
  selector: 'app-audit',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule, 
    TranslateModule, 
    RelativeTimePipe, 
    LoadingSkeletonComponent, 
    EmptyStateComponent
  ],
  templateUrl: './audit.component.html',
  styleUrl: './audit.component.scss',
})
export class AuditComponent implements OnInit {
  private auditSvc = inject(AuditService);

  loading = signal(true);
  logs = signal<AuditLog[]>([]);
  total = signal(0);
  page = signal(1);
  pageSize = 50;
  search = '';
  actionFilter = '';
  statusFilter = '';
  resourceFilter = '';
  dateFrom = '';
  dateTo = '';

  filtered = this.logs; // Simple proxy for template compat
  paginated = this.logs; // Simple proxy for template compat

  totalPages() { return Math.ceil(this.total() / this.pageSize); }
  setPage(p: number) { this.page.set(p); this.loadLogs(); }

  ngOnInit() {
    this.loadLogs();
  }

  loadLogs() {
    this.loading.set(true);
    const params: any = {
      page: this.page(),
      page_size: this.pageSize,
      search: this.search,
      action: this.actionFilter,
      status: this.statusFilter,
      resource_type: this.resourceFilter,
      timestamp_after: this.dateFrom,
      timestamp_before: this.dateTo
    };

    this.auditSvc.getLogs(params).subscribe({
      next: (res) => {
        this.logs.set(res.results || []);
        this.total.set(res.count || 0);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  applyFilter() {
    this.page.set(1);
    this.loadLogs();
  }

  exportCSV() {
    const header = ['Time', 'Actor', 'Action', 'Resource', 'IP'];
    const rows = this.logs().map(l => [
      l.timestamp,
      l.actor,
      l.action,
      l.resource_type,
      l.ip_address
    ]);
    
    const csvContent = [header, ...rows].map(e => e.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `audit_log_${new Date().getTime()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
