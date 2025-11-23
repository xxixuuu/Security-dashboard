// User types
export interface User {
  id: string
  email: string
  username: string
  full_name?: string
  role: 'admin' | 'user' | 'viewer'
  is_active: boolean
  created_at: string
  github_username?: string
  gitlab_username?: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

// Repository types
export interface Repository {
  id: string
  name: string
  full_name: string
  description?: string
  url: string
  provider: 'github' | 'gitlab'
  status: 'active' | 'inactive' | 'archived' | 'error'
  is_private: boolean
  auto_scan: boolean
  total_scans: number
  last_scan_at?: string
  vulnerabilities_count: number
  primary_language?: string
  created_at: string
  updated_at: string
}

// Scan types
export type ScanStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type ScanTrigger = 'manual' | 'scheduled' | 'webhook' | 'api'

export interface Scan {
  id: string
  repository_id: string
  status: ScanStatus
  trigger: ScanTrigger
  commit_sha?: string
  branch?: string
  total_vulnerabilities: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  info_count: number
  started_at?: string
  completed_at?: string
  duration_seconds?: number
  error_message?: string
  ai_summary?: string
  created_at: string
}

// Vulnerability types
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type VulnerabilityType = 'sast' | 'dependency' | 'secret' | 'container' | 'license' | 'code_quality'
export type VulnerabilityStatus = 'open' | 'in_progress' | 'resolved' | 'false_positive' | 'accepted_risk' | 'wont_fix'

export interface Vulnerability {
  id: string
  scan_id: string
  title: string
  description: string
  severity: Severity
  type: VulnerabilityType
  status: VulnerabilityStatus
  scanner: string
  rule_id?: string
  cwe_id?: string
  cve_id?: string
  file_path?: string
  line_number?: number
  code_snippet?: string
  package_name?: string
  package_version?: string
  fixed_version?: string
  cvss_score?: number
  remediation?: string
  ai_suggested_fix?: string
  is_false_positive: boolean
  first_detected_at: string
  last_detected_at: string
  resolved_at?: string
}

// Notification types
export type NotificationType =
  | 'scan_completed'
  | 'scan_failed'
  | 'new_vulnerability'
  | 'critical_vulnerability'
  | 'vulnerability_resolved'
  | 'weekly_summary'
  | 'system_alert'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  is_read: boolean
  created_at: string
  repository_id?: string
  scan_id?: string
}

// Dashboard types
export interface DashboardStats {
  total_repositories: number
  active_scans: number
  total_vulnerabilities: number
  critical_vulnerabilities: number
  high_vulnerabilities: number
  medium_vulnerabilities: number
  low_vulnerabilities: number
  info_vulnerabilities: number
  scans_today: number
  scans_this_week: number
}

export interface VulnerabilityTrend {
  date: string
  critical: number
  high: number
  medium: number
  low: number
}
