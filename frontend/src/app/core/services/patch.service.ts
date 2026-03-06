import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { Patch, PaginatedResponse } from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class PatchService {
  constructor(private api: ApiService) {}

  getPatches(params: any = {}): Observable<PaginatedResponse<Patch>> {
    return this.api.get<PaginatedResponse<Patch>>('/patches/', params);
  }

  getPatchById(id: string): Observable<Patch> {
    return this.api.get<Patch>(`/patches/${id}/`);
  }

  approvePatch(id: string, reason: string = ''): Observable<any> {
    return this.api.post<any>(`/patches/${id}/approve/`, { reason });
  }

  rejectPatch(id: string, reason: string = ''): Observable<any> {
    return this.api.post<any>(`/patches/${id}/reject/`, { reason });
  }

  bulkApprove(patchIds: string[]): Observable<any> {
    return this.api.post<any>('/patches/bulk_approve/', { patch_ids: patchIds });
  }

  getStats(): Observable<any> {
    return this.api.get<any>('/patches/stats/');
  }

  getPatchStats(): Observable<any> {
    return this.getStats();
  }

  reviewPatch(id: string): Observable<any> {
    return this.api.post<any>(`/patches/${id}/review/`, {});
  }

  getComplianceSummary(): Observable<any> {
    return this.api.get<any>('/patches/compliance_summary/');
  }
}
