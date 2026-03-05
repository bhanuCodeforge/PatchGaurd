import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';
import { FormsModule } from '@angular/forms';
import { PatchCatalogComponent } from './patch-catalog.component';
import { PatchService } from '../../core/services/patch.service';
import { NotificationService } from '../../core/services/notification.service';
import { of } from 'rxjs';

describe('PatchCatalogComponent', () => {
  let component: PatchCatalogComponent;
  let fixture: ComponentFixture<PatchCatalogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        PatchCatalogComponent,
        HttpClientTestingModule,
        FormsModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        {
          provide: PatchService,
          useValue: {
            getPatches: () => of({ results: [], count: 0 }),
            approvePatch: () => of({}),
            rejectPatch: () => of({}),
            bulkApprove: () => of({}),
          },
        },
        {
          provide: NotificationService,
          useValue: { success: vi.fn(), error: vi.fn() },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PatchCatalogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
  it('should initialize with empty patches', () => {
    expect(component.patches().length).toBe(0);
  });
});
