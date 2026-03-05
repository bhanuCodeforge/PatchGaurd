import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'severityColor', standalone: true })
export class SeverityColorPipe implements PipeTransform {
  transform(severity: string): string {
    const map: Record<string, string> = {
      critical: '#ef4444',
      high: '#f97316',
      medium: '#eab308',
      low: '#22c55e',
    };
    return map[severity?.toLowerCase()] ?? '#6b7280';
  }
}

@Pipe({ name: 'severityBg', standalone: true })
export class SeverityBgPipe implements PipeTransform {
  transform(severity: string): string {
    const map: Record<string, string> = {
      critical: 'rgba(239,68,68,0.15)',
      high: 'rgba(249,115,22,0.15)',
      medium: 'rgba(234,179,8,0.15)',
      low: 'rgba(34,197,94,0.15)',
    };
    return map[severity?.toLowerCase()] ?? 'rgba(107,114,128,0.15)';
  }
}

@Pipe({ name: 'statusColor', standalone: true })
export class StatusColorPipe implements PipeTransform {
  transform(status: string): string {
    const map: Record<string, string> = {
      online: '#22c55e',
      offline: '#ef4444',
      decommissioned: '#6b7280',
      imported: '#6b7280',
      reviewed: '#3b82f6',
      approved: '#22c55e',
      rejected: '#ef4444',
      superseded: '#a855f7',
      draft: '#6b7280',
      scheduled: '#3b82f6',
      in_progress: '#f59e0b',
      paused: '#f97316',
      completed: '#22c55e',
      failed: '#ef4444',
      cancelled: '#6b7280',
      rolling_back: '#a855f7',
    };
    return map[status?.toLowerCase()] ?? '#6b7280';
  }
}

@Pipe({ name: 'complianceColor', standalone: true })
export class ComplianceColorPipe implements PipeTransform {
  transform(rate: number): string {
    if (rate >= 0.9) return '#22c55e';
    if (rate >= 0.7) return '#eab308';
    return '#ef4444';
  }
}
