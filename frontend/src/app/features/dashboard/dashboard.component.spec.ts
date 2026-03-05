import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';
import { DashboardComponent } from './dashboard.component';
import { ReportService } from '../../core/services/report.service';
import { DeviceService } from '../../core/services/device.service';
import { DeploymentService } from '../../core/services/deployment.service';
import { PatchService } from '../../core/services/patch.service';
import { of } from 'rxjs';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DashboardComponent,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: ReportService,
          useValue: {
            getDashboardStats: () =>
              of({
                total_devices: 100,
                online_devices: 90,
                pending_patches: 5,
                active_deployments: 2,
                compliance_rate: 87,
              }),
          },
        },
        { provide: DeviceService, useValue: { getDevices: () => of({ results: [] }) } },
        { provide: DeploymentService, useValue: { getDeployments: () => of({ results: [] }) } },
        { provide: PatchService, useValue: { getPatches: () => of({ results: [] }) } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should calculate compliance rate', () => {
    expect(component.complianceRate()).toBeGreaterThanOrEqual(0);
  });
});
