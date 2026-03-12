import { Component, OnInit, signal, inject, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { UserService, CSVImportResult } from '../../../core/services/user.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';

const ROLE_COLORS: Record<string, string> = {
  admin: '#7c3aed',
  operator: '#0d9488',
  viewer: '#64748b',
  agent: '#1d4ed8',
};

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TranslateModule,
    ConfirmDialogComponent,
    LoadingSkeletonComponent,
    RelativeTimePipe,
  ],
  templateUrl: './user-management.component.html',
  styleUrl: './user-management.component.scss',
})
export class UserManagementComponent implements OnInit {
  private userSvc = inject(UserService);
  private ns = inject(NotificationService);

  // ── State ─────────────────────────────────────────────────────────────────
  loading = signal(true);
  users = signal<any[]>([]);
  filtered = signal<any[]>([]);

  activeTab = signal<string>('all');
  search = '';
  sourceFilter = '';
  statusFilter = '';
  deptFilter = '';

  currentPage = signal(1);
  pageSize = 10;

  // Panel
  showPanel = signal(false);
  panelMode = signal<'add' | 'edit'>('add');
  saving = signal(false);
  editTarget = signal<any>(null);

  newUser = this._blankUser();

  // Confirm delete
  delVisible = signal(false);
  delTarget = signal<any>(null);

  // Inline actions
  actionMenuOpen = signal<string | null>(null);  // user id with open menu
  roleMenuOpen = signal<string | null>(null);

  // CSV import/export
  csvImporting = signal(false);
  csvResult = signal<CSVImportResult | null>(null);
  csvResultVisible = signal(false);

  // ── Stats ─────────────────────────────────────────────────────────────────
  stats = computed(() => {
    const all = this.users();
    return {
      all: all.length,
      admin: all.filter(u => u.role === 'admin').length,
      operator: all.filter(u => u.role === 'operator').length,
      viewer: all.filter(u => u.role === 'viewer').length,
      agent: all.filter(u => u.role === 'agent').length,
      locked: all.filter(u => u.is_locked).length,
    };
  });

  departments = computed(() => {
    const deps = new Set<string>();
    this.users().forEach(u => { if (u.department) deps.add(u.department); });
    return Array.from(deps).sort();
  });

  totalPages = computed(() => Math.max(1, Math.ceil(this.filtered().length / this.pageSize)));

  pagedUsers = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filtered().slice(start, start + this.pageSize);
  });

  pageNumbers = computed(() => {
    const total = this.totalPages();
    if (total <= 5) return Array.from({ length: total }, (_, i) => i + 1);
    const cur = this.currentPage();
    const pages: (number | '...')[] = [1];
    if (cur > 3) pages.push('...');
    for (let p = Math.max(2, cur - 1); p <= Math.min(total - 1, cur + 1); p++) pages.push(p);
    if (cur < total - 2) pages.push('...');
    pages.push(total);
    return pages;
  });

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  ngOnInit() { this.load(); }

  @HostListener('document:keydown.escape')
  onEsc() {
    this.showPanel.set(false);
    this.actionMenuOpen.set(null);
    this.roleMenuOpen.set(null);
  }

  @HostListener('document:click')
  onDocClick() {
    this.actionMenuOpen.set(null);
    this.roleMenuOpen.set(null);
  }

  load() {
    this.loading.set(true);
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
    const tab = this.activeTab();
    const src = this.sourceFilter;
    const status = this.statusFilter;
    const dept = this.deptFilter;

    this.filtered.set(
      this.users().filter(u => {
        const matchSearch = !s ||
          (u.username || '').toLowerCase().includes(s) ||
          (u.email || '').toLowerCase().includes(s) ||
          (u.full_name || '').toLowerCase().includes(s);
        const matchTab = tab === 'all' || u.role === tab;
        const matchSrc = !src || (u.source || 'local') === src;
        const matchStatus = !status ||
          (status === 'active' && !u.is_locked) ||
          (status === 'locked' && u.is_locked);
        const matchDept = !dept || (u.department || '') === dept;
        return matchSearch && matchTab && matchSrc && matchStatus && matchDept;
      })
    );
    this.currentPage.set(1);
  }

  setTab(tab: string) {
    this.activeTab.set(tab);
    this.applyFilter();
  }

  // ── Panel ─────────────────────────────────────────────────────────────────
  openAddPanel() {
    this.newUser = this._blankUser();
    this.panelMode.set('add');
    this.editTarget.set(null);
    this.showPanel.set(true);
  }

  openEditPanel(u: any, ev: MouseEvent) {
    ev.stopPropagation();
    this.actionMenuOpen.set(null);
    this.newUser = {
      username: u.username,
      email: u.email,
      full_name: u.full_name || '',
      department: u.department || '',
      role: u.role,
      source: u.source || 'local',
      password: '',
      force_password_change: false,
      notify_critical: true,
      notify_deploy: true,
      notify_digest: false,
    };
    this.editTarget.set(u);
    this.panelMode.set('edit');
    this.showPanel.set(true);
  }

  saveUser() {
    if (!this.newUser.username || !this.newUser.email) {
      this.ns.error('Validation', 'Username and email are required.');
      return;
    }
    if (this.panelMode() === 'add' && !this.newUser.password) {
      this.ns.error('Validation', 'Temporary password is required.');
      return;
    }
    this.saving.set(true);
    const obs = this.panelMode() === 'add'
      ? this.userSvc.createUser(this.newUser)
      : this.userSvc.updateRole(this.editTarget().id, this.newUser.role);

    obs.subscribe({
      next: () => {
        this.ns.success('Success', this.panelMode() === 'add' ? `User ${this.newUser.username} created.` : 'User updated.');
        this.showPanel.set(false);
        this.saving.set(false);
        this.load();
      },
      error: (err: any) => {
        const msg = err?.error?.detail || err?.error?.username?.[0] || 'Operation failed.';
        this.ns.error('Error', msg);
        this.saving.set(false);
      },
    });
  }

  // ── Row actions ───────────────────────────────────────────────────────────
  toggleActionMenu(uid: string, ev: MouseEvent) {
    ev.stopPropagation();
    this.roleMenuOpen.set(null);
    this.actionMenuOpen.set(this.actionMenuOpen() === uid ? null : uid);
  }

  toggleRoleMenu(uid: string, ev: MouseEvent) {
    ev.stopPropagation();
    this.actionMenuOpen.set(null);
    this.roleMenuOpen.set(this.roleMenuOpen() === uid ? null : uid);
  }

  changeRole(u: any, role: string, ev?: MouseEvent) {
    ev?.stopPropagation();
    this.roleMenuOpen.set(null);
    this.userSvc.updateRole(u.id, role).subscribe({
      next: () => {
        this.ns.success('Updated', `${u.username} role → ${role}`);
        u.role = role;
      },
      error: () => this.ns.error('Error', 'Failed to change role.'),
    });
  }

  unlock(u: any, ev?: MouseEvent) {
    ev?.stopPropagation();
    this.actionMenuOpen.set(null);
    this.userSvc.unlockAccount(u.id).subscribe({
      next: () => { this.ns.success('Unlocked', `${u.username} unlocked.`); this.load(); },
      error: () => this.ns.error('Error', 'Failed to unlock.'),
    });
  }

  lockUser(u: any, ev?: MouseEvent) {
    ev?.stopPropagation();
    this.actionMenuOpen.set(null);
    // Use update endpoint to set is_active=false or a dedicated lock endpoint
    this.userSvc.lockAccount(u.id).subscribe({
      next: () => { this.ns.success('Locked', `${u.username} locked.`); this.load(); },
      error: () => this.ns.error('Error', 'Failed to lock account.'),
    });
  }

  resetPassword(u: any, ev?: MouseEvent) {
    ev?.stopPropagation();
    this.actionMenuOpen.set(null);
    this.userSvc.resetPassword(u.id).subscribe({
      next: () => this.ns.success('Reset', `Password reset email sent to ${u.email}.`),
      error: () => this.ns.error('Error', 'Failed to reset password.'),
    });
  }

  confirmDelete(u: any, ev?: MouseEvent) {
    ev?.stopPropagation();
    this.actionMenuOpen.set(null);
    this.delTarget.set(u);
    this.delVisible.set(true);
  }

  doDelete() {
    this.delVisible.set(false);
    this.userSvc.deleteUser(this.delTarget().id).subscribe({
      next: () => { this.ns.success('Deleted', `${this.delTarget().username} removed.`); this.load(); },
      error: () => this.ns.error('Error', 'Failed to delete user.'),
    });
  }

  // ── CSV Import / Export ───────────────────────────────────────────────────
  exportCsv() {
    const params: any = {};
    if (this.activeTab() !== 'all') params['role'] = this.activeTab();
    if (this.sourceFilter) params['source'] = this.sourceFilter;
    if (this.statusFilter) params['status'] = this.statusFilter;
    this.userSvc.exportCsv(params).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users_${new Date().toISOString().slice(0,10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.ns.error('Error', 'CSV export failed.'),
    });
  }

  onCsvFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    input.value = '';  // reset so same file can be re-selected
    this.csvImporting.set(true);
    this.csvResult.set(null);
    this.userSvc.importCsv(file).subscribe({
      next: (result: CSVImportResult) => {
        this.csvResult.set(result);
        this.csvResultVisible.set(true);
        this.csvImporting.set(false);
        if (result.created > 0) {
          this.ns.success('Import complete', `${result.created} user(s) created.`);
          this.load();
        }
        if (result.errors > 0 || result.skipped > 0) {
          this.ns.error('Import warnings', `${result.errors} error(s), ${result.skipped} skipped.`);
        }
      },
      error: (err: any) => {
        this.ns.error('Import failed', err?.error?.detail ?? 'Unknown error.');
        this.csvImporting.set(false);
      },
    });
  }

  downloadCsvTemplate() {
    const rows = [
      'username,email,full_name,role,department,source,password',
      'john.doe,john@corp.com,John Doe,viewer,IT Operations,local,TempPass123!',
      'jane.smith,jane@corp.com,Jane Smith,operator,Security,local,TempPass456@',
    ].join('\n');
    const blob = new Blob([rows], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'users_import_template.csv'; a.click();
    URL.revokeObjectURL(url);
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  initials(u: any): string {
    const name = u.full_name || u.username || '';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }

  avatarColor(role: string): string {
    return ROLE_COLORS[role] ?? '#64748b';
  }

  isServiceAccount(u: any): boolean {
    return u.role === 'agent' || u.is_service_account;
  }

  goPage(p: number | '...') {
    if (typeof p === 'number') this.currentPage.set(p);
  }

  private _blankUser() {
    return {
      username: '',
      email: '',
      full_name: '',
      department: '',
      role: 'viewer',
      source: 'local',
      password: '',
      force_password_change: true,
      notify_critical: true,
      notify_deploy: true,
      notify_digest: false,
    };
  }

  readonly ROLES = ['viewer', 'operator', 'admin'];

  readonly ROLE_PERMS: Record<string, { label: string; viewer: boolean; operator: boolean; admin: boolean }[]> = {
    Devices: [
      { label: 'View devices', viewer: true, operator: true, admin: true },
      { label: 'Add / edit devices', viewer: false, operator: true, admin: true },
      { label: 'Decommission devices', viewer: false, operator: false, admin: true },
    ],
    Patches: [
      { label: 'View patches', viewer: true, operator: true, admin: true },
      { label: 'Approve patches', viewer: false, operator: true, admin: true },
      { label: 'Import patches', viewer: false, operator: false, admin: true },
    ],
    Deployments: [
      { label: 'View deployments', viewer: true, operator: true, admin: true },
      { label: 'Create deployments', viewer: false, operator: true, admin: true },
      { label: 'Execute deployments', viewer: false, operator: true, admin: true },
    ],
    Users: [
      { label: 'View users', viewer: false, operator: false, admin: true },
      { label: 'Manage users', viewer: false, operator: false, admin: true },
    ],
  };

  permGroups = Object.keys(this.ROLE_PERMS);
}
