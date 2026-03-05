import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-skeleton',
  standalone: true,
  imports: [CommonModule],
  template: `
    <ng-container [ngSwitch]="variant">
      <div *ngSwitchCase="'kpi-row'" class="kpi-row">
        <div *ngFor="let i of [1, 2, 3, 4]" class="kpi-card shimmer"></div>
      </div>
      <div *ngSwitchCase="'table'" class="table-skel">
        <div class="skel-header shimmer"></div>
        <div *ngFor="let r of rows" class="skel-row shimmer"></div>
      </div>
      <div *ngSwitchCase="'card'" class="card-skel shimmer"></div>
      <div *ngSwitchCase="'chart'" class="chart-skel shimmer"></div>
      <div *ngSwitchDefault class="skel-row shimmer" [style.height.px]="height"></div>
    </ng-container>
  `,
  styles: [
    `
      @keyframes shimmer {
        0% {
          background-position: -400px 0;
        }
        100% {
          background-position: 400px 0;
        }
      }
      .shimmer {
        background: linear-gradient(90deg, #1f2937 25%, #374151 50%, #1f2937 75%);
        background-size: 800px 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 8px;
      }
      .kpi-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
      }
      .kpi-card {
        height: 90px;
        border-radius: 10px;
      }
      .table-skel {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .skel-header {
        height: 44px;
        border-radius: 8px;
      }
      .skel-row {
        height: 52px;
        border-radius: 6px;
      }
      .card-skel {
        height: 200px;
      }
      .chart-skel {
        height: 280px;
      }
    `,
  ],
})
export class LoadingSkeletonComponent {
  @Input() variant: 'kpi-row' | 'table' | 'card' | 'chart' | 'line' = 'line';
  @Input() rows = [1, 2, 3, 4, 5];
  @Input() height = 40;
}
