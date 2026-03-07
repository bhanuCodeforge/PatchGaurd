import { Component, Input, Output, EventEmitter, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { Device } from '../../../core/models/types';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-device-edit',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, TranslateModule],
  templateUrl: './device-edit.component.html',
  styleUrl: './device-edit.component.scss'
})
export class DeviceEditComponent implements OnInit {
  @Input() device!: Device;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<Device>();

  private fb = inject(FormBuilder);
  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);

  editForm!: FormGroup;
  submitting = false;

  ngOnInit() {
    this.editForm = this.fb.group({
      hostname: [this.device.hostname, [Validators.required, Validators.minLength(2)]],
      ip_address: [this.device.ip_address, [Validators.required]],
      environment: [this.device.environment, [Validators.required]],
      tags: [this.device.tags.join(', ')]
    });
  }

  save() {
    if (this.editForm.invalid) return;
    
    this.submitting = true;
    const val = this.editForm.value;
    const payload = {
      ...val,
      tags: val.tags ? val.tags.split(',').map((t: string) => t.trim()).filter((t: string) => !!t) : []
    };

    this.deviceSvc.updateDevice(this.device.id, payload).subscribe({
      next: (updated) => {
        this.ns.success('Success', 'Device updated successfully.');
        this.saved.emit(updated);
        this.submitting = false;
        this.close.emit();
      },
      error: (err) => {
        this.ns.error('Error', err?.error?.detail || 'Failed to update device.');
        this.submitting = false;
      }
    });
  }
}
