import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { DashboardStats } from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class ReportService {
  constructor(private api: ApiService) {}

  getDashboardStats(): Observable<DashboardStats> {
    return this.api.get<DashboardStats>('/reports/dashboard-stats/');
  }

  getComplianceReport(): Observable<any> {
    return this.api.get<any>('/reports/compliance/');
  }
}
