import {
  Component, Input, OnDestroy, AfterViewInit,
  ViewChild, ElementRef, signal, inject, ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { AuthService } from '../../../core/auth/auth.service';
import { NotificationService } from '../../../core/services/notification.service';

type SshState = 'idle' | 'dialog' | 'connecting' | 'connected';
type AuthType  = 'password' | 'key' | 'agent';

interface SshForm {
  host: string;
  port: number;
  username: string;
  authType: AuthType;
  password: string;
  privateKey: string;
  saveConfig: boolean;
}

@Component({
  selector: 'app-ssh-terminal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ssh-terminal.component.html',
  styleUrl: './ssh-terminal.component.scss',
})
export class SshTerminalComponent implements AfterViewInit, OnDestroy {
  @Input() host      = '';
  @Input() port      = 22;
  @Input() deviceName = '';

  @ViewChild('termEl') termEl!: ElementRef<HTMLDivElement>;

  private auth = inject(AuthService);
  private ns   = inject(NotificationService);
  private cdr  = inject(ChangeDetectorRef);

  state      = signal<SshState>('idle');
  sessionId  = signal('');
  cipher     = signal('');
  keyEx      = signal('');
  elapsed    = signal('00:00');
  connecting = signal(false);
  isFullscreen = signal(false);

  form: SshForm = {
    host: '',  port: 22,
    username: '',
    authType: 'password',
    password: '',
    privateKey: '',
    saveConfig: true,
  };

  private term!: Terminal;
  private fit!: FitAddon;
  private ws: WebSocket | null = null;
  private elapsedTimer: ReturnType<typeof setInterval> | null = null;
  private ro: ResizeObserver | null = null;
  private inputHandler: ((d: string) => void) | null = null;

  // ── Lifecycle ────────────────────────────────────────────────────────────
  ngAfterViewInit() {
    // Pre-fill from @Input + saved config
    const saved = this._loadSaved();
    this.form.host     = this.host || saved?.host || '';   // always prefer device IP
    this.form.port     = saved?.port     ?? this.port;
    this.form.username = saved?.username ?? '';
    this.form.authType = saved?.authType ?? 'password';
  }

  ngOnDestroy() {
    this._cleanup();
  }

  // ── Public actions ────────────────────────────────────────────────────────
  openDialog() {
    if (!this.form.host) this.form.host = this.host;
    this.state.set('dialog');
  }

  closeDialog() {
    if (this.state() === 'dialog') this.state.set('idle');
  }

  connect() {
    if (!this.form.host || !this.form.username) return;
    if (this.form.saveConfig) this._saveConfig();

    this.connecting.set(true);
    this.state.set('connecting');
    this._buildTerminal(() => this._openWs());
  }

  demoSession() {
    this.state.set('connecting');
    this.connecting.set(true);
    this._buildTerminal(() => {
      this.connecting.set(false);
      this._runDemo();
    });
  }

  disconnect() {
    this._cleanup();
    this.state.set('idle');
    this.cdr.detectChanges();
  }

  popOut() {
    const url = `about:blank`;
    const w = window.open(url, '_blank', 'width=960,height=640,menubar=no,toolbar=no,location=no');
    if (w) {
      w.document.write(`<html><head><title>SSH – ${this.deviceName}</title>
        <link rel="stylesheet" href="/main.css">
        </head><body style="margin:0;background:#0d0f14"></body></html>`);
    }
  }

  toggleFullscreen() {
    const panel = this.termEl?.nativeElement?.closest('.ssh-panel') as HTMLElement | null;
    if (!panel) return;
    if (!document.fullscreenElement) {
      panel.requestFullscreen().then(() => this.isFullscreen.set(true));
    } else {
      document.exitFullscreen().then(() => this.isFullscreen.set(false));
    }
  }

  // ── Terminal init ──────────────────────────────────────────────────────────
  private _buildTerminal(onReady: () => void) {
    setTimeout(() => {
      if (!this.termEl?.nativeElement) return;

      this.term = new Terminal({
        theme: {
          background:          '#0d0f14',
          foreground:          '#e2e8f0',
          cursor:              '#60a5fa',
          selectionBackground: 'rgba(96,165,250,.28)',
          black:        '#1a1d23', brightBlack:   '#374151',
          red:          '#f87171', brightRed:     '#ef4444',
          green:        '#4ade80', brightGreen:   '#22c55e',
          yellow:       '#fbbf24', brightYellow:  '#f59e0b',
          blue:         '#60a5fa', brightBlue:    '#3b82f6',
          magenta:      '#a78bfa', brightMagenta: '#8b5cf6',
          cyan:         '#34d399', brightCyan:    '#10b981',
          white:        '#e2e8f0', brightWhite:   '#f9fafb',
        },
        fontFamily:  '"JetBrains Mono","Fira Code","Cascadia Code","Consolas",monospace',
        fontSize:    13,
        lineHeight:  1.45,
        cursorBlink: true,
        scrollback:  5000,
      });

      this.fit = new FitAddon();
      this.term.loadAddon(this.fit);
      this.term.open(this.termEl.nativeElement);
      this.fit.fit();

      this.ro = new ResizeObserver(() => { try { this.fit.fit(); } catch {} });
      this.ro.observe(this.termEl.nativeElement);

      this.term.onData(d => this.inputHandler?.(d));
      this.term.onResize(({ cols, rows }) => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'resize', cols, rows }));
        }
      });

      onReady();
    }, 60);
  }

  // ── Real SSH over WebSocket ────────────────────────────────────────────────
  private _openWs() {
    const token = this.auth.getAccessToken();
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url   = `${proto}//${location.host}/ws/ssh?token=${token}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      const { cols, rows } = this.term
        ? { cols: this.term.cols, rows: this.term.rows }
        : { cols: 80, rows: 24 };

      this.ws!.send(JSON.stringify({
        type: 'connect',
        host: this.form.host,   port: this.form.port,
        username: this.form.username,
        auth_type: this.form.authType,
        password:    this.form.password,
        private_key: this.form.privateKey,
        cols, rows,
      }));
    };

    this.ws.onmessage = ev => {
      const msg = JSON.parse(ev.data as string);
      switch (msg.type) {
        case 'connected':
          this.connecting.set(false);
          this.state.set('connected');
          this.sessionId.set(msg.session_id);
          this.cipher.set(msg.cipher);
          this.keyEx.set(msg.key_exchange);
          this._startElapsed();
          this._printBanner(msg.session_id, msg.cipher, msg.key_exchange);
          this.inputHandler = d => {
            if (this.ws?.readyState === WebSocket.OPEN)
              this.ws.send(JSON.stringify({ type: 'input', data: d }));
          };
          this.term.focus();
          this.cdr.detectChanges();
          break;

        case 'output':
          this.term.write(msg.data);
          break;

        case 'error':
          this.connecting.set(false);
          this.ns.error('SSH Error', msg.message);
          this.term.writeln(`\r\n\x1b[31m✕ ${msg.message}\x1b[0m\r\n`);
          setTimeout(() => this.disconnect(), 3000);
          break;

        case 'disconnected':
          this.term.writeln('\r\n\x1b[90mConnection closed.\x1b[0m');
          setTimeout(() => this.disconnect(), 1200);
          break;
      }
    };

    this.ws.onerror = () => {
      this.connecting.set(false);
      this.ns.error('SSH', 'WebSocket connection failed — is the realtime service running?');
      this.state.set('idle');
    };

    this.ws.onclose = () => {
      if (this.state() === 'connected') {
        this.term?.writeln('\r\n\x1b[90mDisconnected.\x1b[0m');
        setTimeout(() => this.disconnect(), 1200);
      }
    };
  }

  // ── Demo session ───────────────────────────────────────────────────────────
  private _runDemo() {
    const host = this.form.host || this.host || '127.0.0.1';
    const dev  = this.deviceName || host;
    const user = this.form.username || 'demo';
    const sid  = 'pg-ssh-demo01';

    this.state.set('connected');
    this.sessionId.set(sid);
    this.cipher.set('AES256-GCM');
    this.keyEx.set('curve25519-sha256');
    this._startElapsed();
    this._printBanner(sid, 'AES256-GCM', 'curve25519-sha256');

    // Fake MOTD
    const w = (s: string) => this.term.writeln(s);
    w(`\x1b[90mLast login: Mon Apr 14 14:32:01 2026 from 10.0.0.15\x1b[0m`);
    w(`\x1b[32mWelcome to Ubuntu 22.04.4 LTS (GNU/Linux 6.5.0-44-generic x86_64)\x1b[0m`);
    w(`\x1b[90m * Documentation:  https://help.ubuntu.com\x1b[0m`);
    w(`\x1b[90m * Management:     https://landscape.canonical.com\x1b[0m`);
    w(``);
    w(`\x1b[33m * 2 security updates pending:\x1b[0m`);
    w(`\x1b[90m   1 critical (CVE-2025-3891 kernel), 1 high (CVE-2025-3754 glibc)\x1b[0m`);
    w(``);

    const prompt = () => this.term.write(`\x1b[32m${user}@${dev}:~$\x1b[0m `);
    prompt();

    let buf = '';
    this.inputHandler = data => {
      if (data === '\r') {
        this.term.writeln('');
        const cmd = buf.trim(); buf = '';
        this._demoCmd(cmd, dev, user, prompt);
      } else if (data === '\x7f') {
        if (buf.length) { buf = buf.slice(0, -1); this.term.write('\b \b'); }
      } else if (data === '\x03') {
        buf = ''; this.term.writeln('^C'); prompt();
      } else if (data >= ' ') {
        buf += data; this.term.write(data);
      }
    };

    this.connecting.set(false);
    this.term.focus();
    this.cdr.detectChanges();
  }

  private _demoCmd(cmd: string, dev: string, user: string, prompt: () => void) {
    const w = (s: string) => this.term.writeln(s);
    switch (cmd) {
      case '': break;
      case 'ls': case 'ls -la':
        w('total 48'); w(`drwxr-xr-x  5 ${user} ${user} 4096 Apr 14 09:12 .`);
        w('drwxr-xr-x  3 root root 4096 Jan  8 2026 ..'); w('-rw-r--r--  1 '+user+' '+user+'  220 Jan  8 2026 .bash_logout');
        w('-rw-r--r--  1 '+user+' '+user+' 3771 Jan  8 2026 .bashrc'); w('drwxr-xr-x  2 '+user+' '+user+' 4096 Apr 14 09:12 logs');
        break;
      case 'pwd':     w('/home/'+user); break;
      case 'whoami':  w(user); break;
      case 'hostname': w(dev); break;
      case 'uname -a': w('Linux '+dev+' 6.5.0-44-generic #44-Ubuntu SMP Thu Apr 10 14:01:42 UTC 2025 x86_64 GNU/Linux'); break;
      case 'uptime':   w(' 14:32:01 up 43 days, 12:14,  1 user,  load average: 0.08, 0.12, 0.09'); break;
      case 'df -h':
        w('Filesystem      Size  Used Avail Use% Mounted on');
        w('/dev/sda1        50G   22G   26G  46% /'); w('tmpfs           3.9G     0  3.9G   0% /dev/shm'); break;
      case 'free -h':
        w('               total   used    free  buff/cache  available');
        w('Mem:            7.7Gi  2.1Gi   4.2Gi  1.4Gi       5.3Gi');
        w('Swap:           2.0Gi     0B   2.0Gi'); break;
      case 'cat /etc/os-release':
        w('NAME="Ubuntu"'); w('VERSION="22.04.4 LTS (Jammy Jellyfish)"'); w('ID=ubuntu'); break;
      case 'exit': case 'logout':
        w('\x1b[90mlogout'); w(`Connection to ${dev} closed.\x1b[0m`);
        setTimeout(() => this.disconnect(), 800); return;
      default:
        if (cmd) w(`\x1b[31mbash: ${cmd}: command not found\x1b[0m \x1b[90m(demo mode)\x1b[0m`);
    }
    prompt();
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  private _printBanner(sid: string, cipher: string, kex: string) {
    const host = this.form.host || this.host;
    const port = this.form.port;
    const dev  = this.deviceName || host;
    this.term.writeln('\r\n\x1b[36m─────────────────────────────────────────────────\x1b[0m');
    this.term.writeln(`\x1b[36m PatchGuard SSH Tunnel \x1b[90m·\x1b[36m ${dev} \x1b[90m·\x1b[36m ${host}:${port}\x1b[0m`);
    this.term.writeln(`\x1b[90m Session ID: ${sid} · Audit logging: enabled\x1b[0m`);
    this.term.writeln(`\x1b[90m Encryption: ${cipher} · Key exchange: ${kex}\x1b[0m`);
    this.term.writeln('\x1b[36m─────────────────────────────────────────────────\x1b[0m\r\n');
  }

  private _startElapsed() {
    let s = 0;
    this.elapsedTimer = setInterval(() => {
      s++;
      const m   = Math.floor(s / 60).toString().padStart(2, '0');
      const sec = (s % 60).toString().padStart(2, '0');
      this.elapsed.set(`${m}:${sec}`);
    }, 1000);
  }

  private _cleanup() {
    clearInterval(this.elapsedTimer!);
    this.elapsedTimer = null;
    this.ro?.disconnect();
    this.inputHandler = null;
    if (this.ws) { this.ws.onclose = null; this.ws.close(); this.ws = null; }
    try { this.term?.dispose(); } catch {}
  }

  private _saveConfig() {
    localStorage.setItem('pg_ssh_cfg', JSON.stringify({
      host: this.form.host, port: this.form.port,
      username: this.form.username, authType: this.form.authType,
    }));
  }

  private _loadSaved() {
    try { return JSON.parse(localStorage.getItem('pg_ssh_cfg') ?? 'null'); }
    catch { return null; }
  }
}
