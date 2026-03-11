import { Injectable, inject } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';

export interface SystemSetting {
  id?: string;
  key: string;
  value: string;
  data: any;
  description?: string;
}

@Injectable({
  providedIn: 'root'
})
export class SettingsService {
  private api = inject(ApiService);

  getSettings(): Observable<SystemSetting[]> {
    return this.api.get<SystemSetting[]>('/settings/');
  }

  getSetting(key: string): Observable<SystemSetting> {
    return this.api.get<SystemSetting>(`/settings/${key}/`);
  }

  updateSetting(key: string, data: Partial<SystemSetting>): Observable<SystemSetting> {
    return this.api.patch<SystemSetting>(`/settings/${key}/`, data);
  }

  // Helper for boolean settings
  getBool(key: string, defaultValue: boolean = false): Observable<boolean> {
    return new Observable<boolean>(obs => {
      this.getSetting(key).subscribe({
        next: (s) => {
          const val = s.value?.toLowerCase();
          obs.next(val === 'true' || val === '1' || val === 'yes');
          obs.complete();
        },
        error: () => {
          obs.next(defaultValue);
          obs.complete();
        }
      });
    });
  }
}
