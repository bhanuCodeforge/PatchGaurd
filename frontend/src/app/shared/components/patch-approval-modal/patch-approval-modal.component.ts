import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-patch-approval-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './patch-approval-modal.component.html',
  styleUrl: './patch-approval-modal.component.scss'
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
