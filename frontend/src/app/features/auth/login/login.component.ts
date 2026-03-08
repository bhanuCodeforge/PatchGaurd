import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { WebsocketService } from '../../../core/services/websocket.service';
import { NotificationService } from '../../../core/services/notification.service';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, TranslateModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private wsService = inject(WebsocketService);
  public notificationService = inject(NotificationService);
  private router = inject(Router);

  loginForm = this.fb.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
    authType: ['local', Validators.required],
    remember: [false],
  });

  isLoading = signal(false);

  constructor() {}

  onSubmit() {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const val = this.loginForm.value;

    this.authService
      .login({
        username: val.username,
        password: val.password,
      })
      .subscribe({
        next: () => {
          this.isLoading.set(false);
          this.notificationService.success(
            'MSG.m_welcome_back',
            'MSG.m_login_success',
          );

          // Connect WebSocket after auth
          this.wsService.connect();

          this.router.navigate(['/dashboard']);
        },
        error: (err: any) => {
          this.isLoading.set(false);
          if (err.status === 401 || err.status === 400) {
            const d = err?.error?.detail;
            const detail = (typeof d === 'string' ? d : null) || err?.error?.non_field_errors?.[0] || '';
            if (detail?.toLowerCase().includes('lock')) {
              this.notificationService.error('MSG.m_account_locked', 'MSG.m_lock_desc');
            } else {
              this.notificationService.error('MSG.m_access_denied', 'MSG.m_invalid_creds');
            }
          } else if (err.status === 403) {
            this.notificationService.error(
              'Account Locked',
              'Multiple failed attempts detected. Try again later.',
            );
          } else {
            this.notificationService.error('Error', 'Unable to reach the authentication server.');
          }
        },
      });
  }
}
