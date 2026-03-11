import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PatchApprovalModalComponent } from './patch-approval-modal.component';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';

describe('PatchApprovalModalComponent', () => {
  let component: PatchApprovalModalComponent;
  let fixture: ComponentFixture<PatchApprovalModalComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PatchApprovalModalComponent, FormsModule, TranslateModule.forRoot()]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(PatchApprovalModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
  
  it('should have default action as approve', () => {
    expect(component.action).toBe('approve');
  });
});
