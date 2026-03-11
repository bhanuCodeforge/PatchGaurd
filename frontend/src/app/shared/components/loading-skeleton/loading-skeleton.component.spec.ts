import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoadingSkeletonComponent } from './loading-skeleton.component';

describe('LoadingSkeletonComponent', () => {
  let component: LoadingSkeletonComponent;
  let fixture: ComponentFixture<LoadingSkeletonComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoadingSkeletonComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(LoadingSkeletonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());

  it('should default to "line" variant', () => {
    expect(component.variant).toBe('line');
  });

  it('should render kpi-row variant', () => {
    component.variant = 'kpi-row';
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.kpi-row')).toBeTruthy();
  });

  it('should render table variant', () => {
    component.variant = 'table';
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.table-skel')).toBeTruthy();
  });

  it('should use custom height for default line variant', () => {
    component.height = 80;
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const row = el.querySelector<HTMLElement>('.skel-row');
    expect(row?.style.height).toBe('80px');
  });
});
