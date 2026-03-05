import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

interface AuditLog {
  id: string;
  timestamp: string;
  actor: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  description: string;
  ip_address: string;
  status: 'success' | 'failure';
}

@Component({
  selector: 'app-audit',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule, RelativeTimePipe, LoadingSkeletonComponent, EmptyStateComponent],
  templateUrl: './audit.component.html',
  styleUrl: './audit.component.scss',
})
export class AuditComponent implements OnInit {
  loading = signal(true);
  logs = signal<AuditLog[]>([]);
  filtered = signal<AuditLog[]>([]);
  page = signal(1);
  pageSize = 50;
  search = '';
  actionFilter = '';
  statusFilter = '';
  dateFrom = '';
  dateTo = '';

  totalPages() { return Math.ceil(this.filtered().length / this.pageSize); }
  paginated() { const s = (this.page() - 1) * this.pageSize; return this.filtered().slice(s, s + this.pageSize); }
  setPage(p: number) { this.page.set(p); }

  ngOnInit() {
    this.loading.set(false);
    this.logs.set([]);
    this.filtered.set([]);
  }

  applyFilter() {
    const s = this.search.toLowerCase();
    const ac = this.actionFilter;
    const st = this.statusFilter;
    this.filtered.set(
      this.logs().filter((l) => {
        if (s && !l.actor.toLowerCase().includes(s) && !l.action.toLowerCase().includes(s) && !l.description.toLowerCase().includes(s)) return false;
        if (ac && l.action !== ac) return false;
        if (st && l.status !== st) return false;
        if (this.dateFrom && l.timestamp < this.dateFrom) return false;
        if (this.dateTo && l.timestamp > this.dateTo) return false;
        return true;
      }),
    );
    this.page.set(1);
  }

  exportCSV() {
    const rows = [['Time', 'Actor', 'Role', 'Action', 'Resource', 'Description', 'IP', 'Status']];
    for (const l of this.filtered()) {
      rows.push([l.timestamp, l.actor, l.actor_role, l.action, l.resource_type, l.description, l.ip_address, l.status]);
    }
    const csv = rows.map((r) => r.map((c) => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `audit-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  }
}
