import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { User, AuthTokens } from '../models/types';
import { jwtDecode } from 'jwt-decode';

interface DecodedToken {
  user_id: number;
  username: string;
  email: string;
  role: 'viewer' | 'operator' | 'admin';
  exp: number;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private _currentUser = signal<User | null>(null);

  // Public readonly signals
  public readonly currentUser = this._currentUser.asReadonly();
  public readonly isAuthenticated = computed(() => this._currentUser() !== null);
  public readonly isAdmin = computed(() => this._currentUser()?.role === 'admin');
  public readonly isOperatorOrAbove = computed(() => {
    const role = this._currentUser()?.role;
    return role === 'admin' || role === 'operator';
  });

  constructor(
    private http: HttpClient,
    private router: Router,
  ) {
    this.restoreSession();
  }

  private restoreSession() {
    const token = localStorage.getItem('access_token');
    if (token) {
      if (this.isTokenValid(token)) {
        this._currentUser.set(this.decodeUserFromToken(token));
      } else {
        this.logout();
      }
    }
  }

  login(credentials: any): Observable<AuthTokens> {
    return this.http.post<AuthTokens>('/api/auth/login/', credentials).pipe(
      tap((tokens) => {
        this.setTokens(tokens);
      }),
    );
  }

  register(data: any): Observable<any> {
    return this.http.post<any>('/api/auth/register/', data).pipe(
      tap((res) => {
        if (res.access && res.refresh) {
          this.setTokens({ access: res.access, refresh: res.refresh });
        }
      }),
    );
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this._currentUser.set(null);
    this.router.navigate(['/login']);
  }

  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private setTokens(tokens: AuthTokens) {
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
    this._currentUser.set(this.decodeUserFromToken(tokens.access));
  }

  private isTokenValid(token: string): boolean {
    try {
      const decoded = jwtDecode<DecodedToken>(token);
      return decoded.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }

  private decodeUserFromToken(token: string): User {
    const decoded = jwtDecode<DecodedToken>(token);
    return {
      id: decoded.user_id,
      username: decoded.username,
      email: decoded.email,
      role: decoded.role,
    };
  }
}
