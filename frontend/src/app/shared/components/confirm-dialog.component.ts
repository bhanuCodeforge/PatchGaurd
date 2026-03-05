import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="visible" class="overlay" (click)="onOverlayClick($event)">
      <div class="dialog">
        <div class="dialog-header" [class]="'dialog-header--' + severity">
          <div class="dialog-icon">
            <span *ngIf="severity === 'danger'">⚠</span>
            <span *ngIf="severity === 'warning'">!</span>
            <span *ngIf="severity === 'info'">?</span>
          </div>
          <h3>{{ title }}</h3>
        </div>
        <div class="dialog-body">
          <p>{{ message }}</p>
          <div *ngIf="confirmText" class="confirm-input">
            <label
              >Type <strong>{{ confirmText }}</strong> to confirm:</label
            >
            <input [(ngModel)]="typedConfirm" [placeholder]="confirmText" />
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" (click)="cancel.emit()">Cancel</button>
          <button
            class="btn-danger"
            [class.btn-warning]="severity === 'warning'"
            [disabled]="confirmText && typedConfirm !== confirmText"
            (click)="confirm.emit()"
          >
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .dialog {
        background: #1f2937;
        border: 1px solid #374151;
        border-radius: 12px;
        width: 440px;
        overflow: hidden;
      }
      .dialog-header {
        padding: 20px 24px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid #374151;
      }
      .dialog-header--danger {
        background: rgba(239, 68, 68, 0.05);
      }
      .dialog-header--warning {
        background: rgba(245, 158, 11, 0.05);
      }
      .dialog-icon {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: bold;
        flex-shrink: 0;
      }
      .dialog-header--danger .dialog-icon {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
      }
      .dialog-header--warning .dialog-icon {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
      }
      .dialog-header--info .dialog-icon {
        background: rgba(59, 130, 246, 0.15);
        color: #3b82f6;
      }
      h3 {
        color: #f9fafb;
        font-size: 16px;
        font-weight: 600;
        margin: 0;
      }
      .dialog-body {
        padding: 20px 24px;
      }
      p {
        color: #9ca3af;
        font-size: 14px;
        line-height: 1.6;
      }
      .confirm-input {
        margin-top: 16px;
      }
      .confirm-input label {
        display: block;
        font-size: 13px;
        color: #9ca3af;
        margin-bottom: 8px;
      }
      .confirm-input strong {
        color: #f9fafb;
      }
      .confirm-input input {
        width: 100%;
        padding: 8px 12px;
        background: #111827;
        border: 1px solid #374151;
        border-radius: 6px;
        color: #f9fafb;
        font-size: 14px;
        outline: none;
      }
      .confirm-input input:focus {
        border-color: #3b82f6;
      }
      .dialog-footer {
        padding: 16px 24px;
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        border-top: 1px solid #374151;
      }
      .btn-secondary {
        padding: 8px 18px;
        background: #374151;
        border: none;
        border-radius: 6px;
        color: #d1d5db;
        font-size: 14px;
        cursor: pointer;
      }
      .btn-secondary:hover {
        background: #4b5563;
      }
      .btn-danger {
        padding: 8px 18px;
        background: #ef4444;
        border: none;
        border-radius: 6px;
        color: white;
        font-size: 14px;
        cursor: pointer;
        font-weight: 500;
      }
      .btn-danger:hover {
        background: #dc2626;
      }
      .btn-danger:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .btn-warning {
        background: #f59e0b !important;
      }
      .btn-warning:hover {
        background: #d97706 !important;
      }
    `,
  ],
})
export class ConfirmDialogComponent {
  @Input() visible = false;
  @Input() title = 'Confirm Action';
  @Input() message = 'Are you sure?';
  @Input() confirmLabel = 'Confirm';
  @Input() severity: 'danger' | 'warning' | 'info' = 'danger';
  @Input() confirmText = '';
  @Output() confirm = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  typedConfirm = '';

  onOverlayClick(e: MouseEvent) {
    if ((e.target as HTMLElement).classList.contains('overlay')) {
      this.cancel.emit();
    }
  }
}
