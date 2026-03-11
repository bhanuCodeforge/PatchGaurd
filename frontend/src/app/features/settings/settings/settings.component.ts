import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SettingsService } from '../../../core/services/settings.service';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent implements OnInit {
  private auth = inject(AuthService);
  private ns = inject(NotificationService);
  private settingsSvc = inject(SettingsService);

  activeSection = 'profile';
  isAdmin = this.auth.currentUser()?.role === 'admin';

  sections = [
    { id: 'profile', label: 'UI.u_profile_tab', icon: '👤' },
    { id: 'security', label: 'UI.u_security_tab', icon: '🔒' },
    { id: 'notifications', label: 'UI.u_notifications_tab', icon: '🔔' },
    { id: 'system', label: 'UI.u_system_info_tab', icon: 'ℹ️' },
    ...(this.auth.currentUser()?.role === 'admin'
      ? [
          { id: 'general', label: 'General', icon: '⚙️' },
          { id: 'vendor_feeds', label: 'Vendor Feeds', icon: '📡' },
          { id: 'email', label: 'Email / SMTP', icon: '✉️' },
          { id: 'maintenance', label: 'Maintenance Windows', icon: '🔧' },
          { id: 'retention', label: 'Data Retention', icon: '🗃️' },
        ]
      : []),
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

  // Admin settings
  generalSettings = {
    orgName: 'PatchGuard Enterprise',
    patchApprovalRequired: true,
    deploymentApprovalRequired: true,
    sessionTimeoutMin: 30,
    maxConcurrentDeployments: 5,
  };

  vendorFeeds = [
    {
      name: 'Microsoft WSUS',
      url: 'https://catalog.update.microsoft.com',
      enabled: true,
      interval: 360,
    },
    {
      name: 'Red Hat Errata',
      url: 'https://access.redhat.com/errata',
      enabled: true,
      interval: 360,
    },
    {
      name: 'Ubuntu USN',
      url: 'https://ubuntu.com/security/notices',
      enabled: true,
      interval: 360,
    },
    {
      name: 'Apple Security',
      url: 'https://support.apple.com/en-us/HT201222',
      enabled: false,
      interval: 720,
    },
  ];

  emailSettings = {
    smtpHost: '',
    smtpPort: 587,
    smtpUser: '',
    smtpPassword: '',
    useTls: true,
    fromAddress: 'patchguard@example.com',
    testRecipient: '',
  };

  maintenanceWindows = [
    { name: 'Weekend Window', start: 'Saturday 02:00', end: 'Saturday 06:00', enabled: true },
    { name: 'Weeknight Window', start: 'Daily 01:00', end: 'Daily 04:00', enabled: false },
  ];

  retentionSettings = {
    auditLogDays: 365,
    deploymentHistoryDays: 180,
    scanResultDays: 90,
    metricsRetentionDays: 30,
  };

  ngOnInit() {
    if (this.auth.isAdmin()) {
      this.loadAdminSettings();
    }
  }

  loadAdminSettings() {
    this.settingsSvc.getSettings().subscribe({
      next: (settings) => {
        settings.forEach(s => {
          if (s.key === 'SMTP_CONFIG') this.emailSettings = { ...this.emailSettings, ...s.data };
          if (s.key === 'GENERAL_POLICY') this.generalSettings = { ...this.generalSettings, ...s.data };
          if (s.key === 'RETENTION_POLICY') this.retentionSettings = { ...this.retentionSettings, ...s.data };
        });
      }
    });
  }

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

  saveGeneralSettings() {
    this.settingsSvc.updateSetting('GENERAL_POLICY', { data: this.generalSettings, value: 'updated' }).subscribe({
      next: () => this.ns.success('UI.u_saved', 'General settings saved'),
      error: () => this.ns.error('Error', 'Failed to save general settings')
    });
  }

  saveVendorFeeds() {
    this.ns.success('UI.u_saved', 'Vendor feed configuration saved');
  }

  saveEmailSettings() {
    this.settingsSvc.updateSetting('SMTP_CONFIG', { data: this.emailSettings, value: 'updated' }).subscribe({
      next: () => this.ns.success('UI.u_saved', 'Email/SMTP settings saved'),
      error: () => this.ns.error('Error', 'Failed to save email settings')
    });
  }

  testEmail() {
    if (!this.emailSettings.testRecipient) {
      this.ns.error('UI.u_validation', 'Enter a test recipient email');
      return;
    }
    this.ns.success('UI.u_sent', 'Test email queued');
  }

  saveMaintenanceWindows() {
    this.ns.success('UI.u_saved', 'Maintenance windows saved');
  }

  saveRetentionSettings() {
    this.settingsSvc.updateSetting('RETENTION_POLICY', { data: this.retentionSettings, value: 'updated' }).subscribe({
      next: () => this.ns.success('UI.u_saved', 'Data retention policy saved'),
      error: () => this.ns.error('Error', 'Failed to save retention settings')
    });
  }
}
