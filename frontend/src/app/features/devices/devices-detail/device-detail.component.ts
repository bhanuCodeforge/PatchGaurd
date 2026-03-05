import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';

@Component({
  selector: 'app-device-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslateModule, StatusBadgeComponent, RelativeTimePipe],
  templateUrl: './device-detail.component.html',
  styleUrl: './device-detail.component.scss',
})
export class DeviceDetailComponent {
  @Input() device: any;
  @Output() close = new EventEmitter<void>();

  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);

  onOverlay(e: MouseEvent) {
    if ((e.target as HTMLElement).classList.contains('flyout-overlay')) this.close.emit();
  }

  scan() {
    this.deviceSvc
      .scanTarget(this.device.id)
      .subscribe(() => this.ns.success('Scan Triggered', `Scanning ${this.device.hostname}`));
  }

  reboot() {
    this.ns.info('Reboot', `Reboot command sent to ${this.device.hostname}`);
  }
}
