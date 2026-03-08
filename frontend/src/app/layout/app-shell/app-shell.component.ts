import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { TopbarComponent } from '../topbar/topbar.component';
import { ToastContainerComponent } from '../../shared/components/toast-container.component';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, SidebarComponent, TopbarComponent, ToastContainerComponent, TranslateModule],
  templateUrl: './app-shell.component.html',
  styleUrl: './app-shell.component.scss',
})
export class AppShellComponent implements OnInit {
  private router = inject(Router);
  pageTitle = 'UI.u_dashboard';

  private titleMap: Record<string, string> = {
    '/dashboard': 'UI.u_dashboard',
    '/devices': 'UI.u_devices',
    '/patches': 'UI.u_patches',
    '/deployments': 'UI.u_deployments',
    '/compliance': 'UI.u_compliance',
    '/audit': 'UI.u_audit_log',
    '/settings/users': 'UI.u_user_management',
    '/settings': 'UI.u_settings',
  };

  ngOnInit() {
    this.router.events
      .pipe(
        filter((e) => e instanceof NavigationEnd),
        map((e) => (e as NavigationEnd).urlAfterRedirects),
      )
      .subscribe((url) => {
        const base = url.split('?')[0];
        for (const [key, val] of Object.entries(this.titleMap)) {
          if (base.startsWith(key)) {
            this.pageTitle = val;
            return;
          }
        }
        this.pageTitle = 'PatchGuard';
      });

    const base = this.router.url.split('?')[0];
    for (const [key, val] of Object.entries(this.titleMap)) {
      if (base.startsWith(key)) {
        this.pageTitle = val;
        return;
      }
    }
  }
}
