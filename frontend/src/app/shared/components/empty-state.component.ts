import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="empty">
      <div class="empty-icon">{{ icon }}</div>
      <h3 class="empty-title">{{ title }}</h3>
      <p class="empty-desc">{{ description }}</p>
      <ng-content></ng-content>
    </div>
  `,
  styles: [
    `
      .empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
        text-align: center;
      }
      .empty-icon {
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
      .empty-title {
        color: #d1d5db;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
      }
      .empty-desc {
        color: #6b7280;
        font-size: 14px;
        line-height: 1.6;
        max-width: 320px;
      }
    `,
  ],
})
export class EmptyStateComponent {
  @Input() icon = '📭';
  @Input() title = 'No data found';
  @Input() description = 'Nothing to display here yet.';
}
