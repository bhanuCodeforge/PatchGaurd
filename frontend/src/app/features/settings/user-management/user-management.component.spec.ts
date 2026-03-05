import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserManagementComponent } from './user-management.component';
import { UserService } from '../../../core/services/user.service';
import { NotificationService } from '../../../core/services/notification.service';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';

describe('UserManagementComponent', () => {
  let component: UserManagementComponent;
  let fixture: ComponentFixture<UserManagementComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserManagementComponent, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        {
          provide: UserService,
          useValue: {
            getUsers: () => of({ results: [] }),
            updateRole: () => of({}),
            unlockAccount: () => of({}),
            createUser: () => of({}),
          },
        },
        { provide: NotificationService, useValue: { success: () => {}, error: () => {} } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(UserManagementComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());
  it('initials should return first 2 chars uppercased', () =>
    expect(component.initials({ username: 'admin' })).toBe('AD'));
  it('showNewPanel should start false', () => expect(component.showNewPanel()).toBeFalsy());
  it('openNewUserPanel should set showNewPanel true', () => {
    component.openNewUserPanel();
    expect(component.showNewPanel()).toBeTruthy();
  });
});
