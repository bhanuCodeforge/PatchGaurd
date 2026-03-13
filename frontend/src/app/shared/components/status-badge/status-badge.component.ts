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
    const v = (this.value || '').toLowerCase();
    
    // Environment Mapping (Matches Design Vibrancy)
    if (this.type === 'env') {
      if (['production', 'prod'].some(s => v.includes(s))) return 'badge-production';
      if (['staging', 'stag'].some(s => v.includes(s))) return 'badge-staging';
      if (['development', 'dev'].some(s => v.includes(s))) return 'badge-development';
      return 'badge-gray';
    }

    // Severity Mapping (Patches/Deployments)
    if (this.type === 'severity') {
      if (v === 'critical') return 'badge-critical';
      if (v === 'high') return 'badge-high';
      if (v === 'medium') return 'badge-medium';
      if (v === 'low') return 'badge-low';
      return 'badge-gray';
    }

    // Workflow Mapping (Approvals)
    if (this.type === 'workflow') {
      if (['approved', 'ready', 'success'].includes(v)) return 'badge-online';
      if (['rejected', 'failed', 'denied'].includes(v)) return 'badge-critical';
      if (['reviewed', 'pending', 'waiting'].includes(v)) return 'badge-maintenance';
      if (['imported', 'draft', 'new'].includes(v)) return 'badge-gray';
      return 'badge-gray';
    }

    // Generic Status Mapping (Fallback)
    if (['online', 'active', 'connected', 'success', 'up'].includes(v)) return 'badge-online';
    if (['offline', 'disconnected', 'locked', 'error', 'down'].includes(v)) return 'badge-offline';
    if (['maintenance', 'warning', 'pending', 'in_progress', 'degraded'].includes(v)) return 'badge-maintenance';
    
    return 'badge-gray';
  }
}
