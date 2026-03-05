import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';
import { SidebarComponent } from './sidebar.component';
import { AuthService } from '../../core/auth/auth.service';
import { signal } from '@angular/core';

describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        SidebarComponent,
        RouterTestingModule,
        HttpClientTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: AuthService,
          useValue: {
            isAdmin: signal(false),
            currentUser: signal({ username: 'testuser', role: 'viewer' }),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display nav sections', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelectorAll('.nav-label').length).toBeGreaterThan(0);
  });

  it('should not show system section for non-admin', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const labels = Array.from(compiled.querySelectorAll('.nav-label')).map((el) =>
      el.textContent?.trim(),
    );
    expect(labels.some((l) => l?.toLowerCase().includes('system'))).toBeFalsy();
  });
});
