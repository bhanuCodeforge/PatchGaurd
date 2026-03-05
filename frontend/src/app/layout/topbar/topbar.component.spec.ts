import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';
import { TopbarComponent } from './topbar.component';
import { AuthService } from '../../core/auth/auth.service';
import { WebsocketService } from '../../core/services/websocket.service';
import { signal } from '@angular/core';

describe('TopbarComponent', () => {
  let component: TopbarComponent;
  let fixture: ComponentFixture<TopbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TopbarComponent,
        RouterTestingModule,
        HttpClientTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: AuthService,
          useValue: {
            currentUser: signal({ username: 'admin', role: 'admin' }),
            logout: vi.fn(),
          },
        },
        {
          provide: WebsocketService,
          useValue: { disconnect: vi.fn() },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TopbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display the title input', () => {
    component.title = 'Dashboard';
    fixture.detectChanges();
    const h1 = fixture.nativeElement.querySelector('.page-title');
    expect(h1.textContent).toContain('Dashboard');
  });

  it('should show user initials', () => {
    expect(component.initials()).toBe('AD');
  });
});
