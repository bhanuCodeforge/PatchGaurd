import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ReactiveFormsModule,
  FormBuilder,
  Validators,
  AbstractControl,
  ValidationErrors,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

function passwordMatch(control: AbstractControl): ValidationErrors | null {
  const pwd = control.get('password');
  const confirm = control.get('confirmPassword');
  if (pwd && confirm && pwd.value !== confirm.value) {
    return { passwordMismatch: true };
  }
  return null;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss'],
})
export class RegisterComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  public notificationService = inject(NotificationService);
  private router = inject(Router);

  isLoading = signal(false);

  registerForm = this.fb.group(
    {
      username: ['', [Validators.required, Validators.minLength(3)]],
      email: ['', [Validators.required, Validators.email]],
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      password: ['', [Validators.required, Validators.minLength(12)]],
      confirmPassword: ['', Validators.required],
    },
    { validators: passwordMatch },
  );

  get pwdMismatch() {
    return (
      this.registerForm.hasError('passwordMismatch') &&
      this.registerForm.get('confirmPassword')?.touched
    );
  }

  onSubmit() {
    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }
    this.isLoading.set(true);
    const { confirmPassword, ...payload } = this.registerForm.value;

    this.authService.register(payload).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.notificationService.success('Account Created', 'Welcome to PatchGuard!');
        this.router.navigate(['/dashboard']);
      },
      error: (err: any) => {
        this.isLoading.set(false);
        // Custom exception handler wraps field errors under detail: { field: [...] }
        const d = err?.error?.detail;
        const msg =
          (d && typeof d === 'object'
            ? d?.username?.[0] || d?.email?.[0] || d?.password?.[0] || d?.non_field_errors?.[0]
            : typeof d === 'string' ? d : null) ||
          err?.error?.username?.[0] ||
          err?.error?.email?.[0] ||
          err?.error?.password?.[0] ||
          err?.error?.non_field_errors?.[0] ||
          'Registration failed.';
        this.notificationService.error('Registration Failed', msg);
      },
    });
  }
}
