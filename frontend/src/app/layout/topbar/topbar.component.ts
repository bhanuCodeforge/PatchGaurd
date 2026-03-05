import { Component, Input, signal, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { AuthService } from '../../core/auth/auth.service';
import { WebsocketService } from '../../core/services/websocket.service';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslateModule],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss',
})
export class TopbarComponent implements OnInit, OnDestroy {
  @Input() title = 'Dashboard';
  auth = inject(AuthService);
  private wsService = inject(WebsocketService);
  private translate = inject(TranslateService);
  private wsSub?: Subscription;

  menuOpen = signal(false);
  wsConnected = signal(false);
  currentLang = 'en';

  initials() {
    const n = this.auth.currentUser()?.username ?? 'U';
    return n.slice(0, 2).toUpperCase();
  }

  constructor() {
    this.translate.setDefaultLang('en');
    this.translate.use('en');
  }

  ngOnInit() {
    this.wsSub = this.wsService.isConnected$.subscribe((connected) => {
      this.wsConnected.set(connected);
    });
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
  }

  setLang(lang: string) {
    this.currentLang = lang;
    this.translate.use(lang);
  }

  toggleMenu() {
    this.menuOpen.update((v) => !v);
  }

  logout() {
    this.wsService.disconnect();
    this.auth.logout();
  }
}
