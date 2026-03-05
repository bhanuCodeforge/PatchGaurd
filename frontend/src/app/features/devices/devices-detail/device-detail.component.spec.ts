import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';
import { DeviceDetailComponent } from './device-detail.component';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { of } from 'rxjs';
import { vi } from 'vitest';

describe('DeviceDetailComponent', () => {
  let component: DeviceDetailComponent;
  let fixture: ComponentFixture<DeviceDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DeviceDetailComponent,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        { provide: DeviceService, useValue: { scanTarget: () => of({}) } },
        {
          provide: NotificationService,
          useValue: { success: vi.fn(), info: vi.fn() },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceDetailComponent);
    component = fixture.componentInstance;
    component.device = {
      id: '1',
      hostname: 'host1',
      ip_address: '10.0.0.1',
      status: 'online',
      compliance_rate: 95,
    };
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
  it('should emit close on overlay click', () => {
    vi.spyOn(component.close, 'emit');
    component.onOverlay({ target: { classList: { contains: () => true } } } as any);
    expect(component.close.emit).toHaveBeenCalled();
  });
});
