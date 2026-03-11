import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { Device, PaginatedResponse } from '../models/types';

@Injectable({
  providedIn: 'root',
})
export class DeviceService {
  constructor(private api: ApiService) {}

  getDevices(params: any = {}): Observable<PaginatedResponse<Device>> {
    return this.api.get<PaginatedResponse<Device>>('/devices/', params);
  }

  getDeviceById(id: string): Observable<Device> {
    return this.api.get<Device>(`/devices/${id}/`);
  }

  createDevice(device: Partial<Device>): Observable<Device> {
    return this.api.post<Device>('/devices/', device);
  }

  updateDevice(id: string, device: Partial<Device>): Observable<Device> {
    return this.api.patch<Device>(`/devices/${id}/`, device);
  }

  deleteDevice(id: string): Observable<void> {
    return this.api.delete<void>(`/devices/${id}/`);
  }

  getDeviceStats(): Observable<any> {
    return this.api.get<any>('/devices/stats/');
  }

  bulkTag(deviceIds: string[], tags: string[], action: 'add' | 'remove' = 'add'): Observable<any> {
    return this.api.post<any>('/devices/bulk_tag/', { device_ids: deviceIds, tags, action });
  }

  scanTarget(id: string): Observable<any> {
    return this.api.post<any>(`/devices/${id}/scan/`, {});
  }

  rebootTarget(id: string): Observable<any> {
    return this.api.post<any>(`/devices/${id}/reboot/`, {});
  }

  getDeviceGroups(params: any = {}): Observable<PaginatedResponse<any>> {
    return this.api.get<PaginatedResponse<any>>('/devices/groups/', params);
  }

  createGroup(group: any): Observable<any> {
    return this.api.post<any>('/devices/groups/', group);
  }

  deleteGroup(id: string): Observable<void> {
    return this.api.delete<void>(`/devices/groups/${id}/`);
  }

  getDevicePatches(id: string, params: any = {}): Observable<PaginatedResponse<any>> {
    return this.api.get<PaginatedResponse<any>>(`/devices/${id}/patches/`, params);
  }

  getDeviceDeployments(id: string): Observable<any[]> {
    return this.api.get<any[]>(`/devices/${id}/deployments/`);
  }

  getInstalledApps(id: string, params: any = {}): Observable<any> {
    return this.api.get<any>(`/devices/${id}/installed_apps/`, params);
  }

  getSystemInfo(id: string): Observable<any> {
    return this.api.get<any>(`/devices/${id}/system_info/`);
  }

  bulkGroup(deviceIds: string[], groupId: string): Observable<any> {
    return this.api.post<any>('/devices/bulk_group/', { device_ids: deviceIds, group_id: groupId });
  }

  updateAgentConfig(id: string, config: any): Observable<any> {
    return this.api.post<any>(`/devices/${id}/agent_config/`, config);
  }

  heartbeat(id: string, payload: any): Observable<any> {
    return this.api.post<any>(`/devices/${id}/heartbeat/`, payload);
  }

  getDeviceActivity(id: string): Observable<any> {
    return this.api.get<any>(`/devices/${id}/activity/`);
  }

  rotateApiKey(id: string): Observable<any> {
    return this.api.post<any>(`/devices/${id}/rotate_key/`, {});
  }

  exportDevices(params: any = {}): Observable<Blob> {
    return this.api.get<Blob>('/devices/export/', { ...params, responseType: 'blob' });
  }

  getSlowLaneSection(id: string, section?: string): Observable<any> {
    const params: any = {};
    if (section) params.section = section;
    return this.api.get<any>(`/devices/${id}/slow_lane_section/`, params);
  }

  requestSlowLaneScan(id: string): Observable<any> {
    return this.api.post<any>(`/devices/${id}/request_slow_lane/`, {});
  }

  requestFastLaneScan(id: string): Observable<any> {
    return this.api.post<any>(`/devices/${id}/request_fast_lane/`, {});
  }

  getInstallerUrl(id: string, os: string): string {
    return `/api/v1/devices/${id}/download_installer/?os=${os}`;
  }

  downloadInstaller(id: string, os: string): Observable<Blob> {
    return this.api.getBlob(`/devices/${id}/download_installer/`, { os });
  }

  triggerGlobalScan(deviceIds?: string[]): Observable<any> {
    return this.api.post<any>('/devices/bulk_scan/', { device_ids: deviceIds });
  }

  // --- New Device Details APIs ---

  getTimeline(id: string, params: any = {}): Observable<PaginatedResponse<any>> {
    return this.api.get<PaginatedResponse<any>>(`/devices/${id}/timeline/`, params);
  }

  installPatch(id: string, patchId: string, lane: 'fast' | 'slow' = 'fast'): Observable<any> {
    return this.api.post<any>(`/devices/${id}/install_patch/`, { patch_id: patchId, lane });
  }

  updateLaneConfig(id: string, config: any): Observable<any> {
    return this.api.post<any>(`/devices/${id}/lane_config/`, config);
  }

  getAlertSummary(id: string): Observable<any> {
    return this.api.get<any>(`/devices/${id}/alert_summary/`);
  }

  getAgentHealth(id: string): Observable<any> {
    return this.api.get<any>(`/devices/${id}/agent_health/`);
  }

  decommissionDevice(id: string): Observable<any> {
    return this.api.post<any>(`/devices/${id}/decommission/`, {});
  }
}
