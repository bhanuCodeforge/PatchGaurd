export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: string | number;
  username: string;
  email: string;
  role: 'viewer' | 'operator' | 'admin';
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface Device {
  id: string;
  hostname: string;
  ip_address: string;
  mac_address: string;
  os_family: string;
  os_name?: string;
  os_version: string;
  status: 'online' | 'offline' | 'decommissioned';
  environment: 'development' | 'staging' | 'production';
  description?: string;
  tags: string[];
  last_seen: string;
  os_arch?: string;
  agent_version?: string;
  groups?: any[];
  metadata?: any;
  compliance_rate?: number;
  inventory_data?: {
    apps?: any[];
    network?: any[];
    storage?: any[];
    [key: string]: any;
  };
}

export interface Patch {
  id: string;
  vendor_id: string;
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'imported' | 'reviewed' | 'approved' | 'rejected' | 'superseded';
  vendor: string;
  description?: string;
  applicable_os: string[];
  requires_reboot: boolean;
  package_name?: string;
  package_version?: string;
  approved_by?: string;
  approved_by_name?: string;
  approved_at?: string;
  status_notes?: string;
  released_at: string;
  affected_device_count?: number;
  device_status_breakdown?: any;
}

export interface Deployment {
  id: string;
  name: string;
  status: 'draft' | 'scheduled' | 'in_progress' | 'paused' | 'cancelled' | 'completed' | 'failed' | 'rolling_back' | 'rolled_back';
  strategy: 'immediate' | 'canary' | 'rolling' | 'maintenance_window';
  total_devices: number;
  completed_devices: number;
  failed_devices: number;
  current_wave: number;
  progress_percentage: number;
  failure_rate: number;
  created_at: string;
}

export interface DashboardStats {
  total_devices: number;
  online_devices: number;
  active_deployments: number;
  pending_patches: number;
}

export interface Envelope<T> {
  event: string;
  payload: T;
  timestamp: string;
}
