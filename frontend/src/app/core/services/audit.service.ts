import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { PaginatedResponse } from '../models/types';

export interface AuditLog {
  id: string;
  timestamp: string;
  actor: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  description: string;
  ip_address: string;
  status: 'success' | 'failure';
}

@Injectable({
  providedIn: 'root'
})
export class AuditService {
  constructor(private api: ApiService) {}

  getLogs(params: any = {}): Observable<PaginatedResponse<AuditLog>> {
    return this.api.get<PaginatedResponse<AuditLog>>('/accounts/audit-logs/', params);
  }
}
