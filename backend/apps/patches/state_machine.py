from django.utils import timezone
from .models import Patch

class PatchStateMachine:
    VALID_TRANSITIONS = {
        Patch.Status.IMPORTED: [Patch.Status.REVIEWED, Patch.Status.REJECTED],
        Patch.Status.REVIEWED: [Patch.Status.APPROVED, Patch.Status.REJECTED],
        Patch.Status.APPROVED: [Patch.Status.SUPERSEDED],
        Patch.Status.REJECTED: [Patch.Status.IMPORTED],
        Patch.Status.SUPERSEDED: [],
    }

    @classmethod
    def can_transition(cls, current_status, new_status):
        allowed = cls.VALID_TRANSITIONS.get(current_status, [])
        return new_status in allowed

    @classmethod
    def get_available_transitions(cls, current_status):
        return cls.VALID_TRANSITIONS.get(current_status, [])

    @classmethod
    def transition(cls, patch, new_status, user=None, reason=""):
        if not cls.can_transition(patch.status, new_status):
            raise ValueError(f"Invalid transition from {patch.status} to {new_status}")

        old_status = patch.status
        patch.status = new_status
        
        if new_status == Patch.Status.APPROVED:
            patch.approved_by = user
            patch.approved_at = timezone.now()

        patch.save()

        # Create audit log if possible
        if user and user.is_authenticated:
            # We must import properly or assume user is a model instance
            from apps.accounts.models import AuditLog
            msg = f"Transitioned patch {patch.vendor_id} from {old_status} to {new_status}"
            if reason:
                msg += f". Reason: {reason}"
                
            AuditLog.objects.create(
                user=user,
                action=msg,
                resource_type="patch",
                resource_id=patch.id
            )
            
        return patch
