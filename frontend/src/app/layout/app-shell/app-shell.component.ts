import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { filter, map } from 'rxjs/operators';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { TopbarComponent } from '../topbar/topbar.component';
import { ToastContainerComponent } from '../../shared/components/toast-container.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, SidebarComponent, TopbarComponent, ToastContainerComponent],
  templateUrl: './app-shell.component.html',
  styleUrl: './app-shell.component.scss',
})
export class AppShellComponent implements OnInit {
  private router = inject(Router);
  pageTitle = 'Dashboard';

  private titleMap: Record<string, string> = {
    '/dashboard': 'Dashboard',
    '/devices': 'Device Inventory',
    '/patches': 'Patch Catalog',
    '/deployments': 'Deployments',
    '/compliance': 'Compliance Report',
    '/audit': 'Audit Log',
    '/settings/users': 'User Management',
    '/settings': 'Settings',
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
