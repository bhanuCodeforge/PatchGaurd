import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';
import { DeploymentListComponent } from './deployment-list.component';
import { DeploymentService } from '../../../core/services/deployment.service';
import { of } from 'rxjs';

describe('DeploymentListComponent', () => {
  let component: DeploymentListComponent;
  let fixture: ComponentFixture<DeploymentListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DeploymentListComponent,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: DeploymentService,
          useValue: { getDeployments: () => of({ results: [], count: 0 }) },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeploymentListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
  it('should show empty state when no deployments', () => {
    expect(component.deployments().length).toBe(0);
  });
});
