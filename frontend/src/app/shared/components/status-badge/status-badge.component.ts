import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './status-badge.component.html',
  styleUrl: './status-badge.component.scss',
})
export class StatusBadgeComponent {
  @Input() value = '';
  @Input() label = '';
  @Input() type: 'severity' | 'status' = 'status';
  @Input() dot = false;

  private statusColorMap: Record<string, string> = {
    online:       '#22c55e',
    offline:      '#ef4444',
    decommissioned:'#6b7280',
    imported:     '#6b7280',
    reviewed:     '#3b82f6',
    approved:     '#22c55e',
    rejected:     '#ef4444',
    superseded:   '#a855f7',
    draft:        '#6b7280',
    scheduled:    '#3b82f6',
    in_progress:  '#f59e0b',
    paused:       '#f97316',
    completed:    '#22c55e',
    failed:       '#ef4444',
    cancelled:    '#6b7280',
    rolling_back: '#a855f7',
  };

  private severityColorMap: Record<string, string> = {
    critical: '#ef4444',
    high:     '#f97316',
    medium:   '#eab308',
    low:      '#22c55e',
  };

  getColor(): string {
    const v = this.value?.toLowerCase();
    if (this.type === 'severity') return this.severityColorMap[v] ?? '#6b7280';
    return this.statusColorMap[v] ?? '#6b7280';
  }

  getStyle() {
    const color = this.getColor();
    return {
      color,
      background: color + '22',
      border: `1px solid ${color}44`,
    };
  }
}
