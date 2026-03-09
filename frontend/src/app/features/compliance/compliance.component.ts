import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { ReportService } from '../../core/services/report.service';
import { DeviceService } from '../../core/services/device.service';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';

@Component({
  selector: 'app-compliance',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule,
    LoadingSkeletonComponent,
    EmptyStateComponent,
    RelativeTimePipe,
  ],
  templateUrl: './compliance.component.html',
  styleUrl: './compliance.component.scss',
})
export class ComplianceComponent implements OnInit {
  private reportSvc = inject(ReportService);
  private deviceSvc = inject(DeviceService);

  loading = signal(true);
  rows = signal<any[]>([]);
  filteredRows = signal<any[]>([]);
  osFilter = '';
  compFilter = '';

  kpis = signal<{ label: string; value: string; color: string }[]>([]);
  sevData = signal<{ label: string; pct: number; color: string }[]>([]);
  compliancePct = signal(0);

  // SLA violations
  slaBreaches = signal<any[]>([]);
  slaLoading = signal(false);

  // Active tab
  activeTab = 'overview';

  ngOnInit() {
    this.reportSvc.getComplianceReport().subscribe({
      next: (r: any) => {
        this.compliancePct.set(Math.round(r.overall ?? 0));
        this.kpis.set([
          {
            label: 'Overall Compliance',
            value: (r.overall ?? 0).toFixed(1) + '%',
            color: this.complianceColor(r.overall ?? 0),
          },
          { label: 'Fully Patched', value: r.compliant_devices ?? '0', color: '#22c55e' },
          { label: 'Non-Compliant', value: r.non_compliant_devices ?? '0', color: '#ef4444' },
          { label: 'Total Devices', value: r.total_devices ?? '0', color: '#60a5fa' },
        ]);
        this.sevData.set([
          { label: 'Critical', pct: r.critical_pct ?? 0, color: '#ef4444' },
          { label: 'High', pct: r.high_pct ?? 0, color: '#f97316' },
          { label: 'Medium', pct: r.medium_pct ?? 0, color: '#eab308' },
          { label: 'Low', pct: r.low_pct ?? 0, color: '#22c55e' },
        ]);
      },
    });
    this.loadDevices();
  }

  loadDevices() {
    this.loading.set(true);
    const params: any = { page_size: 200 };
    if (this.osFilter) params.os_name = this.osFilter;
    this.deviceSvc.getDevices(params).subscribe({
      next: (r) => {
        const list = (r.results ?? []).map((d: any) => ({
          ...d,
          // Real data now available from backend DeviceListSerializer
          compliance_rate: d.compliance_rate ?? 0,
          last_scan: d.last_seen, // fallback for UI
        }));
        this.rows.set(list);
        this.filterTable();
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  filterTable() {
    const comp = this.compFilter;
    this.filteredRows.set(
      this.rows().filter((r) => {
        if (!comp) return true;
        if (comp === 'compliant') return r.compliance_rate >= 90;
        if (comp === 'non_compliant') return r.compliance_rate < 90;
        return true;
      }),
    );
  }

  complianceColor(pct: number): string {
    if (pct >= 90) return '#22c55e';
    if (pct >= 70) return '#eab308';
    return '#ef4444';
  }

  loadSlaBreaches() {
    this.slaLoading.set(true);
    // Derive SLA breaches from non-compliant devices with critical/high missing patches
    this.deviceSvc.getDevices({ page_size: 200 }).subscribe({
      next: (r) => {
        const breaches = (r.results ?? [])
          .filter((d: any) => (d.compliance_rate ?? 100) < 90)
          .map((d: any) => ({
            hostname: d.hostname,
            os_name: d.os_name,
            compliance_rate: d.compliance_rate ?? 0,
            missing_critical: d.missing_critical ?? 0,
            missing_high: d.missing_high ?? 0,
            days_overdue: d.days_since_last_patch ?? 0,
            last_seen: d.last_seen,
          }));
        this.slaBreaches.set(breaches);
        this.slaLoading.set(false);
      },
      error: () => this.slaLoading.set(false),
    });
  }

  exportComplianceCsv() {
    const headers = ['Device', 'OS', 'Compliance %', 'Patched', 'Missing', 'Last Scan'];
    const csvRows = [headers.join(',')];
    for (const r of this.filteredRows()) {
      csvRows.push(
        [
          r.hostname,
          r.os_name,
          r.compliance_rate,
          r.patched_count ?? 0,
          r.missing_count ?? 0,
          r.last_seen ?? '',
        ].join(','),
      );
    }
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compliance-report-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  exportSlaCsv() {
    const headers = [
      'Device',
      'OS',
      'Compliance %',
      'Critical Missing',
      'High Missing',
      'Days Overdue',
    ];
    const csvRows = [headers.join(',')];
    for (const b of this.slaBreaches()) {
      csvRows.push(
        [
          b.hostname,
          b.os_name,
          b.compliance_rate,
          b.missing_critical,
          b.missing_high,
          b.days_overdue,
        ].join(','),
      );
    }
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sla-breaches-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
