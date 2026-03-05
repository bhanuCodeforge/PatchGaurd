import { Injectable } from '@angular/core';
import { Subject, Observable, BehaviorSubject } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { Envelope } from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private socket: WebSocket | null = null;
  private messageSubject = new Subject<Envelope<any>>();
  private connectedSubject = new BehaviorSubject<boolean>(false);
  private reconnectInterval = 5000;

  get isConnected$(): Observable<boolean> {
    return this.connectedSubject.asObservable();
  }

  constructor(private authService: AuthService) {}

  connect() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    const token = this.authService.getAccessToken();
    if (!token) return;

    // Use relative path - proxy will forward /ws to fastapi
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard?token=${token}`;

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.connectedSubject.next(true);
    };

    this.socket.onmessage = (event) => {
      try {
        const data: Envelope<any> = JSON.parse(event.data);
        this.messageSubject.next(data);
      } catch (e) {
        console.error('Error parsing WebSocket message', e);
      }
    };

    this.socket.onclose = () => {
      console.log('WebSocket disconnected. Reconnecting...');
      this.connectedSubject.next(false);
      setTimeout(() => this.connect(), this.reconnectInterval);
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.connectedSubject.next(false);
      this.socket?.close();
    };
  }

  disconnect() {
    if (this.socket) {
      this.socket.onclose = null; // Disable auto-reconnect
      this.socket.close();
      this.socket = null;
    }
    this.connectedSubject.next(false);
  }

  send(event: string, payload: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ event, payload }));
    }
  }

  get messages$(): Observable<Envelope<any>> {
    return this.messageSubject.asObservable();
  }
}
