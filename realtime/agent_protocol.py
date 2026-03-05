from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class MessageEnvelope(BaseModel):
    model_config = ConfigDict(extra='ignore')
    event: str
    payload: Dict[str, Any]

# --- Agent To Server ---

class AgentHeartbeat(BaseModel):
    hostname: str
    os_info: str
    free_disk_space_mb: int

class PatchStatusUpdate(BaseModel):
    patch_vendor_id: str
    status: str # INSTALLED, FAILED, PENDING
    error_log: Optional[str] = None

class SystemInfo(BaseModel):
    os_family: str
    environment: str

# --- Server To Agent ---

class ServerCommand(BaseModel):
    action: str # "START_DEPLOYMENT", "CANCEL_DEPLOYMENT", "FULL_SCAN", "REBOOT"
    args: Dict[str, Any] = {}

# --- Server To Dashboard ---

class DashboardNotification(BaseModel):
    level: str # "info", "warning", "error"
    message: str
    
class DeploymentProgress(BaseModel):
    deployment_id: str
    status: str
    current_wave: int
    progress_percentage: float
    failure_rate: float
