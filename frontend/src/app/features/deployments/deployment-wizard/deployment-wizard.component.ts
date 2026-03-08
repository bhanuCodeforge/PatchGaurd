import { Component, signal, inject, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { PatchService } from '../../../core/services/patch.service';
import { DeviceService } from '../../../core/services/device.service';
import { DeploymentService } from '../../../core/services/deployment.service';
import { NotificationService } from '../../../core/services/notification.service';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';

@Component({
  selector: 'app-deployment-wizard',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule, RelativeTimePipe],
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
  confirmed = signal(false);
  success = signal(false);
  createdDeploymentId = signal<string | null>(null);

  steps = ['Patches', 'Targets', 'Strategy', 'Review'];

  strategies = [
    {
      value: 'immediate',
      label: 'Immediate',
      desc: 'Deploy to all devices simultaneously. Fastest option but highest risk â€” no time to detect issues.',
      pros: ['Fastest completion time', 'Simple execution'],
      cons: ['No rollback window', 'All devices at risk'],
    },
    {
      value: 'canary',
      label: 'Canary',
      desc: 'Small percentage goes first. If canary succeeds, remaining devices deploy in waves.',
      pros: ['Early failure detection', 'Controlled risk exposure'],
      cons: ['Longer total time', 'Requires monitoring canary'],
    },
    {
      value: 'rolling',
      label: 'Rolling',
      desc: 'Deploy wave by wave with configurable delays between each. Balanced risk and speed.',
      pros: ['Steady, predictable pace', 'Per-wave failure checks'],
      cons: ['Slower than immediate', 'No dedicated canary phase'],
    },
  ];

  maintenanceWindows = [
    { label: 'Tonight 02:00â€“06:00 UTC', value: '02:00-06:00' },
    { label: 'Tonight 22:00â€“02:00 UTC', value: '22:00-02:00' },
    { label: 'This Weekend (Sat 00:00â€“06:00 UTC)', value: 'weekend' },
    { label: 'No maintenance window', value: '' },
  ];

  form = {
    name: '',
    description: '',
    patch_ids: [] as string[],
    target_group_ids: [] as string[],
    strategy: 'canary',
    canary_percentage: 5,
    wave_size: 50,
    wave_delay_seconds: 900,
    max_failure_percentage: 5,
    scheduled_at: '',
    maintenance_window: '02:00-06:00',
    requires_reboot: true,
    pre_flight_check: true,
    rollback_on_failure: true,
  };

  allPatches = signal<any[]>([]);
  allGroups = signal<any[]>([]);
  filteredPatches = signal<any[]>([]);
  filteredGroups = signal<any[]>([]);

  patchSearch = '';
  patchSevFilter = '';
  groupSearch = '';
  groupTagFilter = 'all';

  // â”€â”€ Computed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  totalTargetDevices = computed(() =>
    this.allGroups()
      .filter(g => this.form.target_group_ids.includes(g.id))
      .reduce((a, g) => a + (g.device_count || 0), 0)
  );

  selectedGroups = computed(() =>
    this.allGroups().filter(g => this.form.target_group_ids.includes(g.id))
  );

  selectedPatches = computed(() =>
    this.allPatches().filter(p => this.form.patch_ids.includes(p.id))
  );

  criticalPatchCount = computed(() =>
    this.selectedPatches().filter(p => p.severity === 'critical').length
  );

  canaryDeviceCount = computed(() =>
    Math.ceil(this.totalTargetDevices() * this.form.canary_percentage / 100)
  );

  waveCount = computed(() => {
    const total = this.totalTargetDevices();
    if (total === 0) return 0;
    if (this.form.strategy === 'immediate') return 1;
    if (this.form.strategy === 'canary') {
      const rest = total - this.canaryDeviceCount();
      return 1 + Math.ceil(rest / Math.max(1, this.form.wave_size));
    }
    return Math.ceil(total / Math.max(1, this.form.wave_size));
  });

  estDurationHours = computed(() => {
    const waves = this.waveCount();
    if (waves <= 1) return 0.5;
    const delayH = this.form.wave_delay_seconds / 3600;
    return +((waves - 1) * delayH + 0.5).toFixed(1);
  });

  maxFailuresBeforeHalt = computed(() =>
    Math.ceil(this.totalTargetDevices() * this.form.max_failure_percentage / 100)
  );

  waveTimeline = computed(() => {
    const total = this.totalTargetDevices();
    if (total === 0) return [];
    const waves: { label: string; count: number }[] = [];
    const size = Math.max(1, this.form.wave_size);

    if (this.form.strategy === 'canary') {
      waves.push({ label: 'Canary', count: this.canaryDeviceCount() });
      let rem = total - this.canaryDeviceCount();
      let w = 1;
      while (rem > 0) {
        waves.push({ label: `Wave ${w}`, count: Math.min(rem, size) });
        rem -= size; w++;
      }
    } else if (this.form.strategy === 'rolling') {
      let rem = total; let w = 1;
      while (rem > 0) {
        waves.push({ label: `Wave ${w}`, count: Math.min(rem, size) });
        rem -= size; w++;
      }
    } else {
      waves.push({ label: 'All devices', count: total });
    }
    return waves;
  });

  visibleWaves = computed(() => this.waveTimeline().slice(0, 12));
  extraWaves = computed(() => Math.max(0, this.waveTimeline().length - 12));

  largeDeployment = computed(() => this.totalTargetDevices() > 500);

  groupEnvTags = computed(() => {
    const tags = new Set<string>();
    this.allGroups().forEach(g => { if (g.environment) tags.add(g.environment); });
    return Array.from(tags);
  });

  hasRebootPatch = computed(() =>
    this.selectedPatches().some(p => p.requires_reboot || p.reboot_required)
  );

  nextLabel = computed(() => {
    if (this.step() === 1) return 'Continue to strategy';
    if (this.step() === 2) return 'Continue to review';
    return 'Continue';
  });

  // â”€â”€ Lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  ngOnInit() {
    this.patchSvc.getPatches({ status: 'approved', page_size: 200 }).subscribe(r => {
      this.allPatches.set(r.results ?? []);
      this.filteredPatches.set(r.results ?? []);
    });
    this.deviceSvc.getDeviceGroups().subscribe((r: any) => {
      const groups = r.results ?? r;
      this.allGroups.set(groups);
      this.filteredGroups.set(groups);
    });
  }

  // â”€â”€ Filter helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  filterPatches() {
    const s = this.patchSearch.toLowerCase();
    const sev = this.patchSevFilter;
    this.filteredPatches.set(
      this.allPatches().filter(p =>
        (!s || (p.title || '').toLowerCase().includes(s) || (p.vendor_id || '').toLowerCase().includes(s)) &&
        (!sev || p.severity === sev)
      )
    );
  }

  filterGroups() {
    const s = this.groupSearch.toLowerCase();
    const tag = this.groupTagFilter;
    this.filteredGroups.set(
      this.allGroups().filter(g => {
        const matchSearch = !s || (g.name || '').toLowerCase().includes(s) ||
          (g.description || '').toLowerCase().includes(s);
        const matchTag = tag === 'all' || (g.environment || '').toLowerCase() === tag.toLowerCase();
        return matchSearch && matchTag;
      })
    );
  }

  setGroupTag(tag: string) {
    this.groupTagFilter = tag;
    this.filterGroups();
  }

  selectAllShown() {
    this.filteredGroups().forEach(g => {
      if (!this.form.target_group_ids.includes(g.id)) this.form.target_group_ids.push(g.id);
    });
  }

  togglePatch(id: string) {
    const idx = this.form.patch_ids.indexOf(id);
    idx >= 0 ? this.form.patch_ids.splice(idx, 1) : this.form.patch_ids.push(id);
  }

  toggleGroup(id: string) {
    const idx = this.form.target_group_ids.indexOf(id);
    idx >= 0 ? this.form.target_group_ids.splice(idx, 1) : this.form.target_group_ids.push(id);
  }

  // â”€â”€ Navigation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  canNext(): boolean {
    if (this.step() === 0) return this.form.patch_ids.length > 0;
    if (this.step() === 1) return this.form.target_group_ids.length > 0;
    if (this.step() === 2) return !!this.form.name.trim();
    if (this.step() === 3) return this.confirmed();
    return true;
  }

  nextStep() { if (this.canNext()) this.step.update(s => s + 1); }
  prevStep() { this.step.update(s => Math.max(0, s - 1)); }
  cancel() { this.router.navigate(['/deployments']); }
  viewDeployment() { if (this.createdDeploymentId()) this.router.navigate(['/deployments', this.createdDeploymentId()]); }

  // â”€â”€ Lookup helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  getPatchTitle(id: string) { return this.allPatches().find(p => p.id === id)?.title ?? id; }
  getGroupName(id: string) { return this.allGroups().find(g => g.id === id)?.name ?? id; }
  getStrategyLabel(v: string) { return this.strategies.find(s => s.value === v)?.label ?? v; }
  getGroupDeviceCount(id: string) { return this.allGroups().find(g => g.id === id)?.device_count ?? 0; }

  sevClass(sev: string) {
    return { critical: 'sev-critical', high: 'sev-high', medium: 'sev-medium', low: 'sev-low' }
      [sev?.toLowerCase()] ?? 'sev-medium';
  }

  envClass(env: string) {
    return { production: 'env-prod', staging: 'env-staging', development: 'env-dev', mixed: 'env-mixed' }
      [env?.toLowerCase()] ?? 'env-other';
  }

  // â”€â”€ Submit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  submit() {
    if (!this.confirmed()) return;
    this.submitting.set(true);

    const [mwStart, mwEnd] = this.form.maintenance_window
      ? this.form.maintenance_window.split('-')
      : [null, null];

    const payload: any = {
      name: this.form.name,
      description: this.form.description,
      patches: this.form.patch_ids,
      target_groups: this.form.target_group_ids,
      strategy: this.form.strategy,
      canary_percentage: this.form.canary_percentage,
      wave_size: this.form.wave_size,
      wave_delay_minutes: Math.round(this.form.wave_delay_seconds / 60),
      max_failure_percentage: this.form.max_failure_percentage,
      requires_reboot: this.form.requires_reboot,
      maintenance_window_start: mwStart || null,
      maintenance_window_end: mwEnd || null,
    };
    if (this.form.scheduled_at) payload.scheduled_at = this.form.scheduled_at;

    this.deploySvc.createDeployment(payload).subscribe({
      next: (d: any) => {
        this.ns.success('Created', 'Deployment created successfully.');
        this.createdDeploymentId.set(d.id);
        this.success.set(true);
        this.submitting.set(false);
      },
      error: (err: any) => {
        const msg = err?.error?.detail || JSON.stringify(err?.error) || 'Failed to create deployment.';
        this.ns.error('Error', msg);
        this.submitting.set(false);
      },
    });
  }
}


