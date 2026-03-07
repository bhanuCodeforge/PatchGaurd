import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-patch-approval-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  template: `
    <div class="modal-backdrop" (click)="cancel.emit()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h5 class="modal-title">
            <span [class.text-success]="action === 'approve'" [class.text-danger]="action === 'reject'">
              {{ action === 'approve' ? 'Approve Patch' : 'Reject Patch' }}
            </span>
          </h5>
          <button type="button" class="btn-close btn-close-white" (click)="cancel.emit()"></button>
        </div>
        <div class="modal-body">
          <p class="text-secondary small mb-3">
            {{ action === 'approve' 
               ? 'By approving this patch, you allow it to be deployed across the environment.' 
               : 'Rejecting this patch will exclude it from all current and future deployments.' }}
          </p>
          
          <div class="form-group">
            <label class="form-label text-muted small uppercase fw-bold">Reason / Notes</label>
            <textarea 
              class="form-control" 
              rows="4" 
              [(ngModel)]="reason" 
              placeholder="e.g. Critical security fix, approved by CISO, or reasons for rejection..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline-secondary" (click)="cancel.emit()">Cancel</button>
          <button 
            type="button" 
            [class]="action === 'approve' ? 'btn btn-success' : 'btn btn-danger'"
            (click)="submit()">
            Confirm {{ action === 'approve' ? 'Approval' : 'Rejection' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      display: flex; align-items: center; justify-content: center;
      z-index: 1100;
    }
    .modal-content {
      background: #1a1d21;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px;
      width: 100%; max-width: 500px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }
    .modal-header {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      display: flex; align-items: center; justify-content: space-between;
    }
    .modal-title { margin: 0; font-size: 1.1rem; font-weight: 600; }
    .modal-body { padding: 1.25rem; }
    .modal-footer {
      padding: 1rem 1.25rem;
      border-top: 1px solid rgba(255,255,255,0.05);
      display: flex; justify-content: flex-end; gap: 0.75rem;
    }
    .form-label { display: block; margin-bottom: 0.5rem; letter-spacing: 0.05em; }
    .form-control {
      background: #0f1114;
      border: 1px solid rgba(255,255,255,0.1);
      color: white;
      border-radius: 6px;
      padding: 0.75rem;
      width: 100%;
      resize: none;
    }
    .form-control:focus {
      outline: none;
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }
  `]
})
export class PatchApprovalModalComponent {
  @Input() action: 'approve' | 'reject' = 'approve';
  @Output() confirmed = new EventEmitter<string>();
  @Output() cancel = new EventEmitter<void>();

  reason = '';

  submit() {
    this.confirmed.emit(this.reason);
    this.reason = '';
  }
}
