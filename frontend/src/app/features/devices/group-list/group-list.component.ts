import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state.component';

@Component({
  selector: 'app-group-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslateModule, LoadingSkeletonComponent, EmptyStateComponent],
  templateUrl: './group-list.component.html',
  styleUrl: './group-list.component.scss'
})
export class GroupListComponent implements OnInit {
  private deviceSvc = inject(DeviceService);
  private ns = inject(NotificationService);

  loading = signal(true);
  groups = signal<any[]>([]);
  
  showModal = false;
  newGroupName = '';
  newGroupDesc = '';

  ngOnInit() {
    this.loadGroups();
  }

  loadGroups() {
    this.loading.set(true);
    this.deviceSvc.getDeviceGroups().subscribe({
      next: (r) => {
        this.groups.set(r.results || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  createGroup() {
    if (!this.newGroupName.trim()) return;
    this.deviceSvc.createGroup({ name: this.newGroupName, description: this.newGroupDesc }).subscribe({
      next: () => {
        this.ns.success('Success', `Group ${this.newGroupName} created.`);
        this.newGroupName = '';
        this.newGroupDesc = '';
        this.showModal = false;
        this.loadGroups();
      },
      error: () => this.ns.error('Error', 'Failed to create group.')
    });
  }

  deleteGroup(id: string, name: string) {
    if (!confirm(`Are you sure you want to delete ${name}?`)) return;
    this.deviceSvc.deleteGroup(id).subscribe({
      next: () => {
        this.ns.success('Deleted', 'Group removed.');
        this.loadGroups();
      }
    });
  }
}
