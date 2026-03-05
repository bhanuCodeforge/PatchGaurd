import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DeploymentLiveComponent } from './deployment-live.component';
import { DeploymentService } from '../../../core/services/deployment.service';
import { WebsocketService } from '../../../core/services/websocket.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ActivatedRoute } from '@angular/router';
import { of, Subject } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';

describe('DeploymentLiveComponent', () => {
  let component: DeploymentLiveComponent;
  let fixture: ComponentFixture<DeploymentLiveComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeploymentLiveComponent, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        {
          provide: DeploymentService,
          useValue: {
            getDeploymentById: () => of({ name: 'Test', status: 'in_progress' }),
            getTargets: () => of({ results: [] }),
            pause: () => of({}),
            cancel: () => of({}),
            rollback: () => of({}),
          },
        },
        { provide: WebsocketService, useValue: { messages$: new Subject() } },
        { provide: NotificationService, useValue: { success: () => {}, error: () => {} } },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'test-id' } } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(DeploymentLiveComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());
  it('progressPct returns 0 when no stats', () => {
    component['stats'].set({ total: 0, success: 0, failed: 0, pending: 0 });
    expect(component.progressPct()).toBe(0);
  });
  it('heatColor returns green for success', () =>
    expect(component.heatColor('success')).toBe('#22c55e'));
  it('heatColor returns red for failed', () =>
    expect(component.heatColor('failed')).toBe('#ef4444'));
});
