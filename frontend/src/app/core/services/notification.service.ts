import { Injectable, signal } from '@angular/core';

export interface ToastAction {
  label: string;
  variant?: 'primary' | 'default' | 'danger';
  onClick: () => void;
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info' | 'critical' | 'deployment';
  title: string;
  message: string;
  duration: number | null;   // ms — null = never auto-dismiss
  actions?: ToastAction[];
  progress?: number;         // 0-100 (deployment live progress bar)
  progressLabel?: string;    // e.g. "808 of 1,123 devices"
  timestamp: Date;
  exiting?: boolean;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private _toasts = signal<Toast[]>([]);
  readonly toasts = this._toasts.asReadonly();
  private _seq = 0;

  private push(opts: Omit<Toast, 'id' | 'timestamp' | 'exiting'>): string {
    const id = `t${Date.now()}_${++this._seq}`;
    const toast: Toast = { ...opts, id, timestamp: new Date() };

    this._toasts.update(ts => [toast, ...ts].slice(0, 6));

    if (toast.duration !== null) {
      setTimeout(() => this.dismiss(id), toast.duration);
    }
    return id;
  }

  dismiss(id: string) {
    this._toasts.update(ts => ts.map(t => t.id === id ? { ...t, exiting: true } : t));
    setTimeout(() => this._toasts.update(ts => ts.filter(t => t.id !== id)), 350);
  }

  updateProgress(id: string, progress: number, progressLabel?: string) {
    this._toasts.update(ts => ts.map(t =>
      t.id === id ? { ...t, progress, ...(progressLabel !== undefined ? { progressLabel } : {}) } : t
    ));
  }

  /** @deprecated pass id – kept for backward compat */
  remove(toast: Toast) { this.dismiss(toast.id); }

  // ── Convenience methods (backward-compatible signatures) ─────────────────

  success(title: string, message: string) {
    this.push({ type: 'success', title, message, duration: 5000 });
  }

  error(title: string, message: string, actions?: ToastAction[]) {
    this.push({ type: 'error', title, message, duration: null, actions });
  }

  warning(title: string, message: string, actions?: ToastAction[]) {
    this.push({ type: 'warning', title, message, duration: 8000, actions });
  }

  info(title: string, message: string) {
    this.push({ type: 'info', title, message, duration: 5000 });
  }

  critical(title: string, message: string, actions?: ToastAction[]) {
    return this.push({ type: 'critical', title, message, duration: null, actions });
  }

  deployment(
    title: string,
    message: string,
    progress?: number,
    progressLabel?: string,
    actions?: ToastAction[]
  ): string {
    return this.push({ type: 'deployment', title, message, duration: null, progress, progressLabel, actions });
  }
}
