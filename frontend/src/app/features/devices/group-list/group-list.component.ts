import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';

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
  private translate = inject(TranslateService);

  loading = signal(true);
  groups = signal<any[]>([]);
  
  showModal = false;
  newGroupName = '';
  newGroupDesc = '';
  isDynamic = false;
  
  // Rule builder state
  rules: any = {
    os_family: '',
    environment: '',
    tags: []
  };
  newTag = '';

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

  addTag() {
    if (!this.newTag.trim()) return;
    if (!this.rules.tags.includes(this.newTag.trim())) {
      this.rules.tags.push(this.newTag.trim());
    }
    this.newTag = '';
  }

  removeTag(tag: string) {
    this.rules.tags = this.rules.tags.filter((t: string) => t !== tag);
  }

  createGroup() {
    if (!this.newGroupName.trim()) return;
    
    // Build dynamic rules object only if isDynamic is true
    const dynamicRules = this.isDynamic ? {} as any : {};
    if (this.isDynamic) {
      if (this.rules.os_family) dynamicRules.os_family = this.rules.os_family;
      if (this.rules.environment) dynamicRules.environment = this.rules.environment;
      if (this.rules.tags.length > 0) dynamicRules.tags = this.rules.tags;
    }

    const payload = {
      name: this.newGroupName,
      description: this.newGroupDesc,
      is_dynamic: !!this.isDynamic,
      dynamic_rules: dynamicRules
    };

    this.deviceSvc.createGroup(payload).subscribe({
      next: () => {
        this.ns.success(this.translate.instant('UI.u_success'), this.translate.instant('MSG.m_group_created_success', { name: this.newGroupName }));
        this.resetForm();
        this.showModal = false;
        this.loadGroups();
      },
      error: () => this.ns.error(this.translate.instant('UI.u_error'), this.translate.instant('MSG.m_group_create_failed'))
    });
  }

  resetForm() {
    this.newGroupName = '';
    this.newGroupDesc = '';
    this.isDynamic = false;
    this.rules = { os_family: '', environment: '', tags: [] };
    this.newTag = '';
  }

  deleteGroup(id: string, name: string) {
    if (!confirm(this.translate.instant('MSG.m_delete_group_confirm', { name }))) return;
    this.deviceSvc.deleteGroup(id).subscribe({
      next: () => {
        this.ns.success(this.translate.instant('UI.u_deleted'), this.translate.instant('MSG.m_group_deleted_success'));
        this.loadGroups();
      }
    });
  }
}
