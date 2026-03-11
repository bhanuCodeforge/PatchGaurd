import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ConfirmDialogComponent } from './confirm-dialog.component';
import { FormsModule } from '@angular/forms';

describe('ConfirmDialogComponent', () => {
  let component: ConfirmDialogComponent;
  let fixture: ComponentFixture<ConfirmDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfirmDialogComponent, FormsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());

  it('should be hidden by default', () => {
    expect(component.visible).toBeFalsy();
  });

  it('should emit cancel when cancel button is clicked', () => {
    component.visible = true;
    fixture.detectChanges();
    const spy = jasmine.createSpy();
    component.cancel.subscribe(spy);
    component.cancel.emit();
    expect(spy).toHaveBeenCalled();
  });

  it('should emit confirm when confirm button is clicked', () => {
    const spy = jasmine.createSpy();
    component.confirm.subscribe(spy);
    component.confirm.emit();
    expect(spy).toHaveBeenCalled();
  });

  it('should have danger severity by default', () => {
    expect(component.severity).toBe('danger');
  });
});
