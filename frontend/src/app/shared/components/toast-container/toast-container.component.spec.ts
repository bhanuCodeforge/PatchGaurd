import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ToastContainerComponent } from './toast-container.component';
import { NotificationService } from '../../../core/services/notification.service';
import { TranslateModule } from '@ngx-translate/core';

describe('ToastContainerComponent', () => {
  let component: ToastContainerComponent;
  let fixture: ComponentFixture<ToastContainerComponent>;
  let ns: NotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ToastContainerComponent, TranslateModule.forRoot()],
      providers: [NotificationService],
    }).compileComponents();

    fixture = TestBed.createComponent(ToastContainerComponent);
    component = fixture.componentInstance;
    ns = TestBed.inject(NotificationService);
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());

  it('should display a success toast when notification is shown', () => {
    ns.success('MSG.m_welcome_back', 'MSG.m_login_success');
    fixture.detectChanges();
    expect(component.toasts().length).toBe(1);
    expect(component.toasts()[0].type).toBe('success');
  });

  it('should display an error toast when notification is shown', () => {
    ns.error('MSG.m_access_denied', 'MSG.m_invalid_creds');
    fixture.detectChanges();
    expect(component.toasts().length).toBe(1);
    expect(component.toasts()[0].type).toBe('error');
  });

  it('should remove a toast when ns.remove is called', () => {
    ns.info('test', 'message');
    fixture.detectChanges();
    const toast = component.toasts()[0];
    ns.remove(toast);
    fixture.detectChanges();
    expect(component.toasts().length).toBe(0);
  });
});
