import { Injectable, signal } from '@angular/core';

export interface Toast {
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message: string;
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private _toasts = signal<Toast[]>([]);
  public readonly toasts = this._toasts.asReadonly();

  show(toast: Toast) {
    const defaultDuration = toast.duration || 3000;
    const currentToasts = this._toasts();
    this._toasts.set([...currentToasts, toast]);

    setTimeout(() => {
      this.remove(toast);
    }, defaultDuration);
  }

  remove(toast: Toast) {
    this._toasts.update(toasts => toasts.filter(t => t !== toast));
  }

  success(title: string, message: string) {
    this.show({ type: 'success', title, message });
  }

  error(title: string, message: string) {
    this.show({ type: 'error', title, message, duration: 5000 });
  }

  info(title: string, message: string) {
    this.show({ type: 'info', title, message });
  }
}
