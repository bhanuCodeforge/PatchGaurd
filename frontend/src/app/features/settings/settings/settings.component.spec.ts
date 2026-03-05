import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SettingsComponent } from './settings.component';
import { AuthService } from '../../../core/auth/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';

describe('SettingsComponent', () => {
  let component: SettingsComponent;
  let fixture: ComponentFixture<SettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SettingsComponent, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        {
          provide: AuthService,
          useValue: {
            currentUser: () => ({ username: 'admin', email: 'a@b.com' }),
            logout: () => {},
          },
        },
        { provide: NotificationService, useValue: { success: () => {}, error: () => {} } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(SettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());
  it('should default to profile section', () => expect(component.activeSection).toBe('profile'));
  it('should have 4 sections', () => expect(component.sections.length).toBe(4));
  it('saveProfile should not throw', () => expect(() => component.saveProfile()).not.toThrow());
});
