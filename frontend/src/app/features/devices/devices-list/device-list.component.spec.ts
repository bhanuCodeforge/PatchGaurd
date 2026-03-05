import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { DeviceListComponent } from './device-list.component';
import { DeviceService } from '../../../core/services/device.service';
import { NotificationService } from '../../../core/services/notification.service';
import { of } from 'rxjs';

describe('DeviceListComponent', () => {
  let component: DeviceListComponent;
  let fixture: ComponentFixture<DeviceListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DeviceListComponent,
        HttpClientTestingModule,
        RouterTestingModule,
        FormsModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: DeviceService,
          useValue: { getDevices: () => of({ results: [], count: 0 }), scanTarget: () => of({}) },
        },
        { provide: NotificationService, useValue: { success: vi.fn() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeviceListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
  it('should initialize with empty device list', () => {
    expect(component.devices().length).toBe(0);
  });
  it('should compute total pages', () => {
    expect(component.totalPages()).toBe(0);
  });
});
