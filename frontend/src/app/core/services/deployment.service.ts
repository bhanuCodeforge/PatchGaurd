import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { Deployment, PaginatedResponse } from '../models/types';

@Injectable({
  providedIn: 'root',
})
export class DeploymentService {
  constructor(private api: ApiService) {}

  getDeployments(params: any = {}): Observable<PaginatedResponse<Deployment>> {
    return this.api.get<PaginatedResponse<Deployment>>('/deployments/', params);
  }

  getDeploymentById(id: string): Observable<Deployment> {
    return this.api.get<Deployment>(`/deployments/${id}/`);
  }

  createDeployment(payload: any): Observable<Deployment> {
    return this.api.post<Deployment>('/deployments/', payload);
  }

  approve(id: string): Observable<any> {
    return this.api.post<any>(`/deployments/${id}/approve/`);
  }

  execute(id: string): Observable<any> {
    return this.api.post<any>(`/deployments/${id}/execute/`);
  }

  pause(id: string): Observable<any> {
    return this.api.post<any>(`/deployments/${id}/pause/`);
  }

  resume(id: string): Observable<any> {
    return this.api.post<any>(`/deployments/${id}/resume/`);
  }

  cancel(id: string): Observable<any> {
    return this.api.post<any>(`/deployments/${id}/cancel/`);
  }

  rollback(id: string): Observable<any> {
    return this.api.post<any>(`/deployments/${id}/rollback/`);
  }

  getTargets(id: string, params: any = {}): Observable<PaginatedResponse<any>> {
    return this.api.get<PaginatedResponse<any>>(`/deployments/${id}/targets/`, params);
  }

  /** Task 11.5/11.8 — Fetch persistent DeploymentEvent audit log. */
  getDeploymentEvents(id: string, params: any = {}): Observable<any> {
    return this.api.get<any>(`/deployments/${id}/events/`, params);
  }
}
