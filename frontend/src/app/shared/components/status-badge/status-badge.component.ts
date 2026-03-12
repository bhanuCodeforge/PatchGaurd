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
  @Input() type: 'severity' | 'status' | 'env' | 'workflow' = 'status';
  @Input() dot = true;

  getBadgeClass(): string {
    const v = this.value?.toLowerCase() || '';
    
    // Environment Mapping
    if (this.type === 'env') {
      if (v.includes('prod')) return 'badge-production';
      if (v.includes('stag')) return 'badge-staging';
      if (v.includes('dev')) return 'badge-development';
      return 'badge-gray';
    }

    // Severity Mapping
    if (this.type === 'severity') {
      if (v === 'critical') return 'badge-critical';
      if (v === 'high') return 'badge-high';
      if (v === 'medium') return 'badge-medium';
      if (v === 'low') return 'badge-low';
      return 'badge-gray';
    }

    // Workflow Mapping
    if (this.type === 'workflow') {
      if (v === 'approved') return 'badge-online';
      if (v === 'rejected') return 'badge-critical';
      if (v === 'reviewed') return 'badge-maintenance';
      if (v === 'imported') return 'badge-gray';
      return 'badge-gray';
    }

    // Generic Status Mapping
    if (v === 'online' || v === 'active' || v === 'connected' || v === 'success') return 'badge-online';
    if (v === 'offline' || v === 'disconnected' || v === 'locked' || v === 'error') return 'badge-offline';
    if (v === 'maintenance' || v === 'warning' || v === 'pending' || v === 'in_progress') return 'badge-maintenance';
    
    return 'badge-gray';
  }
}
