import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { User, PaginatedResponse } from '../models/types';

export interface SAMLConfig {
  id?: string;
  name: string;
  sp_entity_id?: string;
  idp_entity_id: string;
  idp_sso_url: string;
  idp_slo_url?: string;
  idp_x509_cert: string;
  attribute_mapping?: Record<string, string>;
  default_role?: string;
  auto_create_users?: boolean;
  auto_update_attrs?: boolean;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CSVImportResult {
  created: number;
  skipped: number;
  errors: number;
  created_users: string[];
  skipped_rows: { row: number; username: string; reason: string }[];
  error_rows: { row: number; errors: any }[];
}

@Injectable({ providedIn: 'root' })
export class UserService {
  constructor(private api: ApiService, private http: HttpClient) {}

  // ── User CRUD ─────────────────────────────────────────────────────────────
  getUsers(params: any = {}): Observable<PaginatedResponse<User>> {
    return this.api.get<PaginatedResponse<User>>('/users/', params);
  }

  getMe(): Observable<User> {
    return this.api.get<User>('/users/me/');
  }

  createUser(payload: any): Observable<User> {
    return this.api.post<User>('/users/', payload);
  }

  updateUser(id: string, payload: any): Observable<any> {
    return this.api.patch<any>(`/users/${id}/`, payload);
  }

  deleteUser(id: string): Observable<any> {
    return this.api.delete<any>(`/users/${id}/`);
  }

  // ── User actions ──────────────────────────────────────────────────────────
  updateRole(id: string, role: string): Observable<any> {
    return this.api.post<any>(`/users/${id}/change_role/`, { role });
  }

  unlockAccount(id: string): Observable<any> {
    return this.api.post<any>(`/users/${id}/unlock/`);
  }

  lockAccount(id: string): Observable<any> {
    return this.api.post<any>(`/users/${id}/lock/`);
  }

  resetPassword(id: string): Observable<any> {
    return this.api.post<any>(`/users/${id}/reset_password/`);
  }

  // ── CSV Import / Export ───────────────────────────────────────────────────
  exportCsv(params: any = {}): Observable<Blob> {
    return this.api.getBlob('/users/export-csv/', params);
  }

  importCsv(file: File): Observable<CSVImportResult> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<CSVImportResult>('/api/v1/users/import-csv/', form);
  }

  // ── Audit logs ────────────────────────────────────────────────────────────
  getAuditLogs(params: any = {}): Observable<PaginatedResponse<any>> {
    return this.api.get<PaginatedResponse<any>>('/users/audit-logs/', params);
  }

  // ── SAML Configurations ───────────────────────────────────────────────────
  getSAMLConfigs(): Observable<PaginatedResponse<SAMLConfig>> {
    return this.api.get<PaginatedResponse<SAMLConfig>>('/saml/configs/');
  }

  createSAMLConfig(payload: Partial<SAMLConfig>): Observable<SAMLConfig> {
    return this.api.post<SAMLConfig>('/saml/configs/', payload);
  }

  updateSAMLConfig(id: string, payload: Partial<SAMLConfig>): Observable<SAMLConfig> {
    return this.api.put<SAMLConfig>(`/saml/configs/${id}/`, payload);
  }

  deleteSAMLConfig(id: string): Observable<any> {
    return this.api.delete<any>(`/saml/configs/${id}/`);
  }

  getPublicSAMLProviders(): Observable<{ id: string; name: string }[]> {
    return this.api.get<{ id: string; name: string }[]>('/saml/providers/');
  }

  getSAMLLoginUrl(configId: string): Observable<{ redirect_url: string }> {
    return this.api.get<{ redirect_url: string }>(`/saml/${configId}/login/`);
  }

  getSAMLMetadataUrl(configId: string): string {
    return `/api/v1/saml/${configId}/metadata/`;
  }
}
