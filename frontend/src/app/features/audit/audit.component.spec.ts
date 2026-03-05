import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AuditComponent } from './audit.component';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TranslateModule } from '@ngx-translate/core';

describe('AuditComponent', () => {
  let component: AuditComponent;
  let fixture: ComponentFixture<AuditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuditComponent, HttpClientTestingModule, TranslateModule.forRoot()],
    }).compileComponents();
    fixture = TestBed.createComponent(AuditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());
  it('should start with empty filtered logs', () => expect(component.filtered().length).toBe(0));
  it('totalPages returns 0 for empty', () => expect(component.totalPages()).toBe(0));
  it('exportCSV should not throw', () => expect(() => component.exportCSV()).not.toThrow());
});
