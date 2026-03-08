import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { AuthService } from '../../core/auth/auth.service';

interface NavItem {
  label: string;
  icon: SafeHtml;
  route: string;
  badge?: number;
  adminOnly?: boolean;
}

const SVG = (path: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;

const ICONS: Record<string, string> = {
  dashboard: SVG('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>'),
  deployments: SVG('<path d="M22 2L11 13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>'),
  devices: SVG('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'),
  patches: SVG('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'),
  groups: SVG('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'),
  compliance: SVG('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'),
  audit: SVG('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>'),
  users: SVG('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
  settings: SVG('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
};

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, TranslateModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  private auth = inject(AuthService);
  private san = inject(DomSanitizer);
  isAdmin = this.auth.isAdmin;
  userName = computed(() => this.auth.currentUser()?.username ?? 'User');
  userRole = computed(() => this.auth.currentUser()?.role ?? '');
  initials = computed(() => {
    const n = this.auth.currentUser()?.username ?? 'U';
    return n.slice(0, 2).toUpperCase();
  });

  private icon(key: string): SafeHtml {
    return this.san.bypassSecurityTrustHtml(ICONS[key] ?? '');
  }

  overviewItems: NavItem[] = [];
  manageItems: NavItem[] = [];
  reportItems: NavItem[] = [];
  systemItems: NavItem[] = [];

  constructor() {
    this.overviewItems = [
      { label: 'UI.u_dashboard', icon: this.icon('dashboard'), route: '/dashboard' },
      { label: 'UI.u_deployments', icon: this.icon('deployments'), route: '/deployments' },
    ];
    this.manageItems = [
      { label: 'UI.u_devices', icon: this.icon('devices'), route: '/devices' },
      { label: 'UI.u_groups', icon: this.icon('groups'), route: '/devices/groups' },
      { label: 'UI.u_patches', icon: this.icon('patches'), route: '/patches' },
    ];
    this.reportItems = [
      { label: 'UI.u_compliance', icon: this.icon('compliance'), route: '/compliance' },
      { label: 'UI.u_audit_log', icon: this.icon('audit'), route: '/audit' },
    ];
    this.systemItems = [
      { label: 'UI.u_user_management', icon: this.icon('users'), route: '/settings/users', adminOnly: true },
      { label: 'UI.u_settings', icon: this.icon('settings'), route: '/settings', adminOnly: true },
    ];
  }
}
