import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  constructor(private http: HttpClient) {}

  get<T>(path: string, params: any = {}): Observable<T> {
    let httpParams = new HttpParams();
    Object.keys(params).forEach((key) => {
      if (params[key] !== null && params[key] !== undefined) {
        httpParams = httpParams.append(key, String(params[key]));
      }
    });

    return this.http.get<T>(`/api/v1${path}`, { params: httpParams });
  }

  post<T>(path: string, body: any = {}): Observable<T> {
    return this.http.post<T>(`/api/v1${path}`, body);
  }

  put<T>(path: string, body: any = {}): Observable<T> {
    return this.http.put<T>(`/api/v1${path}`, body);
  }

  patch<T>(path: string, body: any = {}): Observable<T> {
    return this.http.patch<T>(`/api/v1${path}`, body);
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(`/api/v1${path}`);
  }

  getBlob(path: string, params: any = {}): Observable<Blob> {
    let httpParams = new HttpParams();
    Object.keys(params).forEach((key) => {
      if (params[key] !== null && params[key] !== undefined) {
        httpParams = httpParams.append(key, String(params[key]));
      }
    });
    return this.http.get(`/api/v1${path}`, { params: httpParams, responseType: 'blob' });
  }
}
