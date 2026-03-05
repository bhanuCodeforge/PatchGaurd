import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink, Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { PatchService } from '../../../core/services/patch.service';
import { DeviceService } from '../../../core/services/device.service';
import { DeploymentService } from '../../../core/services/deployment.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-deployment-wizard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslateModule],
  templateUrl: './deployment-wizard.component.html',
  styleUrl: './deployment-wizard.component.scss',
})
export class DeploymentWizardComponent implements OnInit {
  private patchSvc = inject(PatchService);
  private deviceSvc = inject(DeviceService);
  private deploySvc = inject(DeploymentService);
  private ns = inject(NotificationService);
  private router = inject(Router);

  step = signal(0);
  submitting = signal(false);
  steps = [
    'WIZARD.STEP_PATCHES',
    'WIZARD.STEP_TARGETS',
    'WIZARD.STEP_STRATEGY',
    'WIZARD.STEP_REVIEW',
  ];
  strategies = [
    {
      value: 'immediate',
      label: 'Immediate',
      desc: 'All devices at once. Fastest but riskiest.',
      icon: '⚡',
    },
    {
      value: 'canary',
      label: 'Canary',
      desc: 'Small % first, then full rollout if healthy.',
      icon: '🐦',
    },
    {
      value: 'rolling',
      label: 'Rolling',
      desc: 'Wave by wave with configurable delays.',
      icon: '≡',
    },
  ];

  form = {
    name: '',
    description: '',
    patch_ids: [] as string[],
    target_device_ids: [] as string[],
    strategy: 'rolling',
    batch_size: 25,
    scheduled_at: '',
    auto_reboot: false,
    rollback_on_failure: true,
  };

  allPatches = signal<any[]>([]);
  allDevices = signal<any[]>([]);
  filteredPatches = signal<any[]>([]);
  filteredDevices = signal<any[]>([]);

  patchSearch = '';
  patchSevFilter = '';
  deviceSearch = '';

  ngOnInit() {
    this.patchSvc.getPatches({ status: 'approved', page_size: 200 }).subscribe((r) => {
      this.allPatches.set(r.results ?? []);
      this.filteredPatches.set(r.results ?? []);
    });
    this.deviceSvc.getDevices({ page_size: 200 }).subscribe((r) => {
      this.allDevices.set(r.results ?? []);
      this.filteredDevices.set(r.results ?? []);
    });
  }

  filterPatches() {
    const s = this.patchSearch.toLowerCase();
    const sev = this.patchSevFilter;
    this.filteredPatches.set(
      this.allPatches().filter(
        (p) =>
          (!s ||
            p.title.toLowerCase().includes(s) ||
            (p.vendor_id || '').toLowerCase().includes(s)) &&
          (!sev || p.severity === sev),
      ),
    );
  }

  filterDevices() {
    const s = this.deviceSearch.toLowerCase();
    this.filteredDevices.set(
      this.allDevices().filter(
        (d) => !s || d.hostname.toLowerCase().includes(s) || (d.ip_address || '').includes(s),
      ),
    );
  }

  togglePatch(id: string) {
    const idx = this.form.patch_ids.indexOf(id);
    idx >= 0 ? this.form.patch_ids.splice(idx, 1) : this.form.patch_ids.push(id);
  }
  toggleDevice(id: string) {
    const idx = this.form.target_device_ids.indexOf(id);
    idx >= 0 ? this.form.target_device_ids.splice(idx, 1) : this.form.target_device_ids.push(id);
  }

  canNext(): boolean {
    if (this.step() === 0) return this.form.patch_ids.length > 0;
    if (this.step() === 1) return this.form.target_device_ids.length > 0;
    if (this.step() === 2) return !!this.form.name.trim();
    return true;
  }

  nextStep() {
    if (this.canNext()) this.step.update((s) => s + 1);
  }
  prevStep() {
    this.step.update((s) => s - 1);
  }

  getPatchTitle(id: string) {
    return this.allPatches().find((p) => p.id === id)?.title ?? id;
  }
  getDeviceHostname(id: string) {
    return this.allDevices().find((d) => d.id === id)?.hostname ?? id;
  }

  submit() {
    this.submitting.set(true);
    const payload: any = { ...this.form };
    if (!payload.scheduled_at) delete payload.scheduled_at;
    this.deploySvc.createDeployment(payload).subscribe({
      next: (d: any) => {
        this.ns.success('Created', 'Deployment created successfully.');
        this.router.navigate(['/deployments', d.id]);
      },
      error: () => {
        this.ns.error('Error', 'Failed to create deployment.');
        this.submitting.set(false);
      },
    });
  }
}
