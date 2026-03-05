import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ComplianceComponent } from './compliance.component';
import { ReportService } from '../../core/services/report.service';
import { DeviceService } from '../../core/services/device.service';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';

describe('ComplianceComponent', () => {
  let component: ComplianceComponent;
  let fixture: ComponentFixture<ComplianceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ComplianceComponent, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        {
          provide: ReportService,
          useValue: {
            getComplianceReport: () =>
              of({
                overall: 85,
                compliant_devices: 10,
                non_compliant_devices: 2,
                total_devices: 12,
              }),
          },
        },
        { provide: DeviceService, useValue: { getDevices: () => of({ results: [] }) } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ComplianceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());
  it('complianceColor returns green for >=90', () =>
    expect(component.complianceColor(90)).toBe('#22c55e'));
  it('complianceColor returns yellow for 70-89', () =>
    expect(component.complianceColor(75)).toBe('#eab308'));
  it('complianceColor returns red for <70', () =>
    expect(component.complianceColor(60)).toBe('#ef4444'));
});
