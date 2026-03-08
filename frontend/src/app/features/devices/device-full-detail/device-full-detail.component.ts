import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { StatusBadgeComponent } from '../../../shared/components/status-badge.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';
import { Device } from '../../../core/models/types';
import { WebsocketService } from '../../../core/services/websocket.service';
import { Subscription } from 'rxjs';

import { trigger, transition, style, animate, query, stagger } from '@angular/animations';

@Component({
  selector: 'app-device-full-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    TranslateModule,
    StatusBadgeComponent,
    LoadingSkeletonComponent,
    RelativeTimePipe
  ],
  templateUrl: './device-full-detail.component.html',
  styleUrl: './device-full-detail.component.scss',
  animations: [
    trigger('listAnimation', [
      transition('* <=> *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translateY(15px)' }),
          stagger('50ms', [
            animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
          ])
        ], { optional: true })
      ])
    ]),
    trigger('tabChange', [
      transition(':enter', [
        style({ opacity: 0, scale: 0.98 }),
        animate('200ms ease-out', style({ opacity: 1, scale: 1 }))
      ])
    ])
  ]
})
export class DeviceFullDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);
  private ws = inject(WebsocketService);
  private wsSub?: Subscription;

  loading = signal(true);
  device = signal<Device | null>(null);
  patches = signal<any[]>([]);
  deployments = signal<any[]>([]);
  isEditing = signal(false);
  activeTab = signal('patches');
  inventoryTab = signal('system');
  appSearch = signal('');
  editData = { hostname: '', description: '' };
  configData = { log_level: 'info', heartbeat_interval: 60 };

  patchCounts = computed(() => {
    const ps = this.patches();
    return {
      installed: ps.filter(p => p.state === 'installed').length,
      pending:   ps.filter(p => p.state === 'pending' || p.state === 'missing').length,
      failed:    ps.filter(p => p.state === 'failed').length,
    };
  });

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadDevice(id);
      this.setupWebsocket(id);
    } else {
      this.router.navigate(['/devices']);
    }
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
  }

  setupWebsocket(id: string) {
    this.wsSub = this.ws.messages$.subscribe(msg => {
      const current = this.device();
      if (!current || msg.payload?.device_id !== id) return;

      if (msg.event === 'agent_heartbeat') {
        this.device.update(d => d ? { ...d, metadata: { ...d.metadata, ...msg.payload } } : null);
      } else if (msg.event === 'agent_inventory_info') {
        this.device.update(d => d ? { ...d, inventory_data: msg.payload.inventory } : null);
      } else if (msg.event === 'status_change') {
        this.device.update(d => d ? { ...d, status: msg.payload.status } : null);
      } else if (msg.event === 'scan_results') {
        this.ns.success('Scan Complete', `New patches discovered for ${current.hostname}`);
        this.loadPatches(id);
      }
    });
  }

  loadDevice(id: string) {
    this.loading.set(true);
    this.deviceSvc.getDeviceById(id).subscribe({
      next: (d) => {
        this.device.set(d);
        this.editData = { hostname: d.hostname, description: d.description || '' };
        // Populate current config from metadata if available
        this.configData = { 
          log_level: d.metadata?.log_level || 'info', 
          heartbeat_interval: d.metadata?.heartbeat_interval || 60 
        };
        this.loadPatches(id);
        this.loadDeployments(id);
        this.loading.set(false);
      },
      error: () => {
        this.ns.error('Error', 'Failed to load device details.');
        this.router.navigate(['/devices']);
      }
    });
  }

  loadPatches(id: string) {
    this.deviceSvc.getDevicePatches(id).subscribe(r => this.patches.set(r.results || []));
  }

  loadDeployments(id: string) {
    this.deviceSvc.getDeviceDeployments(id).subscribe(dls => this.deployments.set(dls || []));
  }

  scan() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.scanTarget(d.id).subscribe(() => this.ns.success('Scan Started', `Remote scan initiated for ${d.hostname}`));
  }

  reboot() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.rebootTarget(d.id).subscribe(() => this.ns.info('Reboot', `Reboot command sent to ${d.hostname}`));
  }

  delete() {
    const d = this.device();
    if (!d || !confirm(`Are you sure you want to delete ${d.hostname}?`)) return;
    this.deviceSvc.deleteDevice(d.id).subscribe({
      next: () => {
        this.ns.success('Deleted', `Device ${d.hostname} has been removed.`);
        this.router.navigate(['/devices']);
      }
    });
  }

  toggleEdit() {
    this.isEditing.set(!this.isEditing());
  }

  save() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.updateDevice(d.id, this.editData).subscribe({
      next: (updated) => {
        this.device.set(updated);
        this.isEditing.set(false);
        this.ns.success('Updated', 'Device properties updated.');
      },
      error: () => this.ns.error('Error', 'Failed to update device.')
    });
  }

  updateConfig() {
    const d = this.device();
    if (!d) return;
    this.deviceSvc.updateAgentConfig(d.id, this.configData).subscribe({
      next: () => {
        this.ns.success('Config Sent', 'Agent configuration update command published.');
      },
      error: () => this.ns.error('Error', 'Failed to send config update.')
    });
  }

  get filteredApps() {
    const apps = this.device()?.inventory_data?.apps || [];
    const search = this.appSearch().toLowerCase();
    if (!search) return apps;
    return apps.filter(a => 
      (a.name?.toLowerCase().includes(search)) || 
      (a.publisher?.toLowerCase().includes(search))
    );
  }
}
