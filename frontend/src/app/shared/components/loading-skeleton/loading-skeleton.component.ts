import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-skeleton',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './loading-skeleton.component.html',
  styleUrl: './loading-skeleton.component.scss',
})
export class LoadingSkeletonComponent {
  @Input() variant: 'kpi-row' | 'table' | 'card' | 'chart' | 'line' = 'line';
  @Input() rows = [1, 2, 3, 4, 5];
  @Input() height = 40;
}
