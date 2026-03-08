import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent {
  auth = inject(AuthService);
  private ns = inject(NotificationService);

  activeSection = 'profile';
  sections = [
    { id: 'profile', label: 'UI.u_profile_tab', icon: '👤' },
    { id: 'security', label: 'UI.u_security_tab', icon: '🔒' },
    { id: 'notifications', label: 'UI.u_notifications_tab', icon: '🔔' },
    { id: 'system', label: 'UI.u_system_info_tab', icon: 'ℹ️' },
  ];

  profile = {
    name: this.auth.currentUser()?.username ?? '',
    email: this.auth.currentUser()?.email ?? '',
  };

  pwd = { current: '', new: '', confirm: '' };

  notifPrefs = [
    { label: 'Deployment Completed', desc: 'Alert when a deployment finishes.', enabled: true },
    { label: 'Deployment Failed', desc: 'Alert when a deployment fails.', enabled: true },
    { label: 'Critical Patch', desc: 'Alert on new critical severity patch.', enabled: true },
    { label: 'Device Offline', desc: 'Alert when monitored device goes offline.', enabled: false },
  ];

  sysInfo = [
    { key: 'Application', value: 'PatchGuard v1.0.0' },
    { key: 'Django Backend', value: 'localhost:8000' },
    { key: 'Realtime Service', value: 'localhost:8001' },
    { key: 'Celery Broker', value: 'Redis' },
    { key: 'Build', value: new Date().toISOString().split('T')[0] },
  ];

  saveProfile() {
    this.ns.success('UI.u_saved', 'MSG.m_profile_updated');
  }

  changePassword() {
    if (!this.pwd.current || !this.pwd.new) {
      this.ns.error('UI.u_validation', 'MSG.m_fields_required');
      return;
    }
    if (this.pwd.new !== this.pwd.confirm) {
      this.ns.error('UI.u_validation', 'MSG.m_pwd_mismatch');
      return;
    }
    if (this.pwd.new.length < 12) {
      this.ns.error('UI.u_validation', 'MSG.m_pwd_min');
      return;
    }
    this.ns.success('UI.u_changed', 'MSG.m_pwd_updated');
    this.auth.logout();
  }

  saveNotifPrefs() {
    this.ns.success('UI.u_saved', 'MSG.m_notif_saved');
  }
}
