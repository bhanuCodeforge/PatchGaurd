import { Routes } from '@angular/router';
import { authGuard, roleGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./features/auth/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: '',
    loadComponent: () =>
      import('./layout/app-shell/app-shell.component').then((m) => m.AppShellComponent),
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'devices',
        loadComponent: () =>
          import('./features/devices/devices-list/device-list.component').then(
            (m) => m.DeviceListComponent,
          ),
      },
      {
        path: 'devices/:id',
        loadComponent: () =>
          import('./features/devices/devices-list/device-list.component').then(
            (m) => m.DeviceListComponent,
          ),
      },
      {
        path: 'patches',
        loadComponent: () =>
          import('./features/patches/patch-catalog.component').then((m) => m.PatchCatalogComponent),
      },
      {
        path: 'deployments',
        loadComponent: () =>
          import('./features/deployments/deployment-list/deployment-list.component').then(
            (m) => m.DeploymentListComponent,
          ),
      },
      {
        path: 'deployments/new',
        loadComponent: () =>
          import('./features/deployments/deployment-wizard/deployment-wizard.component').then(
            (m) => m.DeploymentWizardComponent,
          ),
      },
      {
        path: 'deployments/:id',
        loadComponent: () =>
          import('./features/deployments/deployment-live/deployment-live.component').then(
            (m) => m.DeploymentLiveComponent,
          ),
      },
      {
        path: 'compliance',
        loadComponent: () =>
          import('./features/compliance/compliance.component').then((m) => m.ComplianceComponent),
      },
      {
        path: 'audit',
        loadComponent: () =>
          import('./features/audit/audit.component').then((m) => m.AuditComponent),
      },
      {
        path: 'settings/users',
        loadComponent: () =>
          import('./features/settings/user-management/user-management.component').then(
            (m) => m.UserManagementComponent,
          ),
        canActivate: [roleGuard],
        data: { role: 'admin' },
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./features/settings/settings/settings.component').then(
            (m) => m.SettingsComponent,
          ),
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: 'login' },
];
