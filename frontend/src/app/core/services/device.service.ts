import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { Device, PaginatedResponse } from '../models/types';

@Injectable({
  providedIn: 'root'
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

  getDevicePatches(id: string, params: any = {}): Observable<PaginatedResponse<any>> {
    return this.api.get<PaginatedResponse<any>>(`/devices/${id}/patches/`, params);
  }
}
