import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-device-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslateModule, StatusBadgeComponent, RelativeTimePipe, ConfirmDialogComponent],
  templateUrl: './device-detail.component.html',
  styleUrl: './device-detail.component.scss',
})
export class DeviceDetailComponent {
  @Input() device: any;
  @Output() close = new EventEmitter<void>();
  @Output() edit = new EventEmitter<any>();
  @Output() deleted = new EventEmitter<string>();

  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);
  private router = inject(Router);
  private translate = inject(TranslateService);

  showRebootDialog = false;

  onOverlay(e: MouseEvent) {
    if ((e.target as HTMLElement).classList.contains('flyout-overlay')) this.close.emit();
  }

  scan() {
    this.deviceSvc
      .scanTarget(this.device.id)
      .subscribe(() => this.ns.success('Scan Triggered', `Scanning ${this.device.hostname}`));
  }

  reboot() {
    this.showRebootDialog = true;
  }

  confirmReboot() {
    this.showRebootDialog = false;
    this.deviceSvc
      .rebootTarget(this.device.id)
      .subscribe(() => {
        const title = this.translate.instant('UI.u_reboot_title');
        const msg = this.translate.instant('MSG.m_reboot_confirm', { hostname: this.device.hostname });
        this.ns.info(title, msg);
      });
  }

  delete() {
    if (!confirm(`Are you sure you want to delete ${this.device.hostname}?`)) return;
    this.deviceSvc.deleteDevice(this.device.id).subscribe(() => {
      this.ns.success('Deleted', `Device ${this.device.hostname} removed.`);
      this.deleted.emit(this.device.id);
      this.close.emit();
    });
  }
}
