import { Injectable, signal } from '@angular/core';

export type Theme = 'dark' | 'light';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly STORAGE_KEY = 'pg-theme';

  theme = signal<Theme>(this._load());

  constructor() {
    this._apply(this.theme());
  }

  toggle() {
    const next: Theme = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    this._apply(next);
    localStorage.setItem(this.STORAGE_KEY, next);
  }

  private _load(): Theme {
    const saved = localStorage.getItem(this.STORAGE_KEY) as Theme | null;
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  private _apply(theme: Theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
  }
}
