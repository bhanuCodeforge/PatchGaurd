import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { UserService } from '../../../core/services/user.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule,
    ConfirmDialogComponent,
    LoadingSkeletonComponent,
    EmptyStateComponent,
    RelativeTimePipe,
  ],
  templateUrl: './user-management.component.html',
  styleUrl: './user-management.component.scss',
})
export class UserManagementComponent implements OnInit {
  private userSvc = inject(UserService);
  private ns = inject(NotificationService);

  loading = signal(true);
  users = signal<any[]>([]);
  filtered = signal<any[]>([]);
  search = '';
  roleFilter = '';
  showNewPanel = signal(false);
  creating = signal(false);
  delVisible = signal(false);
  delTarget = signal<any>(null);

  newUser = { username: '', email: '', role: 'viewer', password: '' };

  ngOnInit() {
    this.load();
  }

  load() {
    this.userSvc.getUsers({ page_size: 200 }).subscribe({
      next: (r) => {
        this.users.set(r.results ?? []);
        this.applyFilter();
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  applyFilter() {
    const s = this.search.toLowerCase();
    const r = this.roleFilter;
    this.filtered.set(
      this.users().filter(
        (u) =>
          (!s ||
            u.username.toLowerCase().includes(s) ||
            (u.email || '').toLowerCase().includes(s)) &&
          (!r || u.role === r),
      ),
    );
  }

  initials(u: any): string {
    return (u.username ?? u.email ?? '?').slice(0, 2).toUpperCase();
  }

  changeRole(u: any, role: string) {
    this.userSvc.updateRole(u.id, role).subscribe({
      next: () => this.ns.success('Updated', `${u.username} role changed to ${role}.`),
      error: () => this.ns.error('Error', 'Failed to update role.'),
    });
  }

  unlock(u: any) {
    this.userSvc.unlockAccount(u.id).subscribe({
      next: () => {
        this.ns.success('Unlocked', `${u.username} account unlocked.`);
        this.load();
      },
      error: () => this.ns.error('Error', 'Failed to unlock account.'),
    });
  }

  openNewUserPanel() {
    this.newUser = { username: '', email: '', role: 'viewer', password: '' };
    this.showNewPanel.set(true);
  }

  createUser() {
    if (!this.newUser.username || !this.newUser.email || !this.newUser.password) {
      this.ns.error('Validation', 'Please fill in all required fields.');
      return;
    }
    this.creating.set(true);
    this.userSvc.createUser(this.newUser).subscribe({
      next: () => {
        this.ns.success('Created', `User ${this.newUser.username} created.`);
        this.showNewPanel.set(false);
        this.creating.set(false);
        this.load();
      },
      error: () => {
        this.ns.error('Error', 'Failed to create user.');
        this.creating.set(false);
      },
    });
  }

  confirmDel(u: any) {
    this.delTarget.set(u);
    this.delVisible.set(true);
  }
  doDelete() {
    this.delVisible.set(false);
    this.ns.success('Note', 'User deletion requires admin backend action.');
  }
}
