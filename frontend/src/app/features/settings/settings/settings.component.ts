import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from '../../../core/auth/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SettingsService } from '../../../core/services/settings.service';
import { UserService, SAMLConfig } from '../../../core/services/user.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule, ConfirmDialogComponent],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent implements OnInit {
  private auth = inject(AuthService);
  private ns = inject(NotificationService);
  private settingsSvc = inject(SettingsService);
  private userSvc = inject(UserService);

  activeSection = 'profile';
  isAdmin = this.auth.currentUser()?.role === 'admin';

  sections = [
    { id: 'profile', label: 'UI.u_profile_tab', icon: '👤' },
    { id: 'security', label: 'UI.u_security_tab', icon: '🔒' },
    { id: 'notifications', label: 'UI.u_notifications_tab', icon: '🔔' },
    { id: 'system', label: 'UI.u_system_info_tab', icon: 'ℹ️' },
    ...(this.auth.currentUser()?.role === 'admin'
      ? [
          { id: 'general',      label: 'General',           icon: '⚙️' },
          { id: 'vendor_feeds', label: 'Vendor Feeds',       icon: '📡' },
          { id: 'email',        label: 'Email / SMTP',       icon: '✉️' },
          { id: 'saml',         label: 'SAML / SSO',         icon: '🔐' },
          { id: 'maintenance',  label: 'Maintenance Windows',icon: '🔧' },
          { id: 'retention',    label: 'Data Retention',     icon: '🗃️' },
        ]
      : []),
  ];

  // ── SAML state ─────────────────────────────────────────────────────────────
  samlConfigs: SAMLConfig[]    = [];
  samlLoading                  = false;
  samlPanelOpen                = false;
  samlSaving                   = false;
  samlEditTarget: SAMLConfig | null = null;
  samlDeleteVisible            = false;
  samlDeleteTarget: SAMLConfig | null = null;
  readonly origin              = window.location.origin;

  samlForm: Partial<SAMLConfig> & { is_active: boolean; auto_create_users: boolean; auto_update_attrs: boolean } = this._blankSaml();
  samlAttrMappings: { samlAttr: string; userField: string }[] = [];

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
      this.loadSamlConfigs();
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

  // ── SAML methods ──────────────────────────────────────────────────────────
  loadSamlConfigs() {
    this.samlLoading = true;
    this.userSvc.getSAMLConfigs().subscribe({
      next: (r) => { this.samlConfigs = r.results ?? []; this.samlLoading = false; },
      error: ()  => { this.samlLoading = false; },
    });
  }

  openSamlPanel(cfg?: SAMLConfig) {
    this.samlEditTarget = cfg ?? null;
    if (cfg) {
      this.samlForm = {
        name: cfg.name, idp_entity_id: cfg.idp_entity_id,
        idp_sso_url: cfg.idp_sso_url, idp_slo_url: cfg.idp_slo_url ?? '',
        idp_x509_cert: cfg.idp_x509_cert, sp_entity_id: cfg.sp_entity_id ?? '',
        default_role: cfg.default_role ?? 'viewer',
        auto_create_users: cfg.auto_create_users ?? true,
        auto_update_attrs: cfg.auto_update_attrs ?? true,
        is_active: cfg.is_active ?? true,
      };
      // Explode attribute_mapping JSON into editable rows
      this.samlAttrMappings = Object.entries(cfg.attribute_mapping ?? {})
        .map(([samlAttr, userField]) => ({ samlAttr, userField }));
    } else {
      this.samlForm         = this._blankSaml();
      this.samlAttrMappings = [
        { samlAttr: 'email',     userField: 'email'     },
        { samlAttr: 'cn',        userField: 'full_name'  },
        { samlAttr: 'role',      userField: 'role'       },
      ];
    }
    this.samlPanelOpen = true;
  }

  addAttrMapping()           { this.samlAttrMappings.push({ samlAttr: '', userField: '' }); }
  removeAttrMapping(i: number) { this.samlAttrMappings.splice(i, 1); }

  saveSamlConfig() {
    if (!this.samlForm.name || !this.samlForm.idp_entity_id || !this.samlForm.idp_sso_url || !this.samlForm.idp_x509_cert) {
      this.ns.error('Validation', 'Name, IdP Entity ID, SSO URL, and Certificate are required.');
      return;
    }
    // Collapse attribute mapping rows back to JSON
    const attribute_mapping: Record<string, string> = {};
    this.samlAttrMappings.filter(m => m.samlAttr && m.userField)
      .forEach(m => { attribute_mapping[m.samlAttr] = m.userField; });

    const payload: Partial<SAMLConfig> = { ...this.samlForm, attribute_mapping };
    this.samlSaving = true;
    const obs = this.samlEditTarget
      ? this.userSvc.updateSAMLConfig(this.samlEditTarget.id!, payload)
      : this.userSvc.createSAMLConfig(payload);

    obs.subscribe({
      next: () => {
        this.ns.success('Saved', this.samlEditTarget ? 'IdP updated.' : 'IdP created.');
        this.samlSaving = false; this.samlPanelOpen = false;
        this.loadSamlConfigs();
      },
      error: (err: any) => {
        const msg = err?.error?.detail ?? JSON.stringify(err?.error ?? 'Save failed.');
        this.ns.error('Error', msg); this.samlSaving = false;
      },
    });
  }

  confirmDeleteSaml(cfg: SAMLConfig) { this.samlDeleteTarget = cfg; this.samlDeleteVisible = true; }

  doDeleteSaml() {
    this.samlDeleteVisible = false;
    if (!this.samlDeleteTarget?.id) return;
    this.userSvc.deleteSAMLConfig(this.samlDeleteTarget.id).subscribe({
      next: () => { this.ns.success('Removed', `${this.samlDeleteTarget!.name} removed.`); this.loadSamlConfigs(); },
      error: ()  => this.ns.error('Error', 'Failed to remove IdP.'),
    });
  }

  samlMetadataUrl(id: string): string { return this.userSvc.getSAMLMetadataUrl(id); }

  copySamlUrl(id: string) {
    navigator.clipboard.writeText(`${this.origin}/api/v1/saml/${id}/metadata/`);
    this.ns.success('Copied', 'SP metadata URL copied to clipboard.');
  }

  private _blankSaml() {
    return {
      name: '', idp_entity_id: '', idp_sso_url: '', idp_slo_url: '',
      idp_x509_cert: '', sp_entity_id: '', default_role: 'viewer',
      auto_create_users: true, auto_update_attrs: true, is_active: true,
    };
  }
}
