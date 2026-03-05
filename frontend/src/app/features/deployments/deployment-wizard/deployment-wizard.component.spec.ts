import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { DeploymentWizardComponent } from './deployment-wizard.component';
import { PatchService } from '../../../core/services/patch.service';
import { DeviceService } from '../../../core/services/device.service';
import { DeploymentService } from '../../../core/services/deployment.service';
import { NotificationService } from '../../../core/services/notification.service';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';

describe('DeploymentWizardComponent', () => {
  let component: DeploymentWizardComponent;
  let fixture: ComponentFixture<DeploymentWizardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DeploymentWizardComponent,
        HttpClientTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        provideRouter([]),
        { provide: PatchService, useValue: { getPatches: () => of({ results: [] }) } },
        { provide: DeviceService, useValue: { getDevices: () => of({ results: [] }) } },
        { provide: DeploymentService, useValue: { createDeployment: () => of({}) } },
        { provide: NotificationService, useValue: { success: () => {}, error: () => {} } },      ],
    }).compileComponents();
    fixture = TestBed.createComponent(DeploymentWizardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());
  it('should start at step 0', () => expect(component.step()).toBe(0));
  it('canNext should be false with no patches selected', () =>
    expect(component.canNext()).toBeFalsy());
  it('should have 4 steps', () => expect(component.steps.length).toBe(4));
  it('getPatchTitle should return id if not found', () =>
    expect(component.getPatchTitle('abc')).toBe('abc'));
});