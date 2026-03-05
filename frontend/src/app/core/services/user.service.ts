import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { User, PaginatedResponse } from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  constructor(private api: ApiService) {}

  getUsers(params: any = {}): Observable<PaginatedResponse<User>> {
    return this.api.get<PaginatedResponse<User>>('/users/', params);
  }

  getMe(): Observable<User> {
    return this.api.get<User>('/users/me/');
  }

  createUser(payload: any): Observable<User> {
    return this.api.post<User>('/users/', payload);
  }

  updateRole(id: string, role: string): Observable<any> {
    return this.api.post<any>(`/users/${id}/change_role/`, { role });
  }

  unlockAccount(id: string): Observable<any> {
    return this.api.post<any>(`/users/${id}/unlock/`);
  }
}
