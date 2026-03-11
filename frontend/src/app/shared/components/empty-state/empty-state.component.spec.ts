import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EmptyStateComponent } from './empty-state.component';

describe('EmptyStateComponent', () => {
  let component: EmptyStateComponent;
  let fixture: ComponentFixture<EmptyStateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmptyStateComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(EmptyStateComponent);
    component = fixture.componentInstance;
    component.title = 'No results';
    fixture.detectChanges();
  });

  it('should create', () => expect(component).toBeTruthy());

  it('should render the default icon', () => {
    expect(component.icon).toBe('📭');
  });

  it('should render the custom title', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.empty-title')?.textContent?.trim()).toBe('No results');
  });

  it('should render the default description', () => {
    expect(component.description).toBe('Nothing to display here yet.');
  });
});
