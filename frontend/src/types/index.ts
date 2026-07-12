// ── Domain Models ──

export interface MetricPoint {
  timestamp: number;
  metric_name: string;
  value: number;
  tags: Record<string, string>;
}

export interface AnomalyEvent {
  id?: string;
  metric: string;
  timestamp: number;
  value?: number;
  score: number;
  detector: string;
  severity: 'info' | 'warning' | 'critical';
  context: Record<string, unknown>;
}

export interface AlertEvent {
  id: string;
  metric: string;
  rule_id: string;
  severity: 'info' | 'warning' | 'critical';
  status: 'open' | 'resolved';
  triggered_at: number;
  resolved_at?: number;
  message: string;
}

export interface AlertRule {
  id: string;
  name: string;
  enabled: boolean;
  metric_pattern: string;
  rule_type: 'threshold' | 'anomaly_score' | 'anomaly_burst' | 'sustained_drift';
  detector_config: Record<string, unknown>;
  thresholds: Record<string, number>;
  severity: 'info' | 'warning' | 'critical';
  cooldown_seconds: number;
  actions: string[];
  filters: Record<string, string>;
  created_at?: number;
  updated_at?: number;
}

export interface DetectorSettings {
  enabled: boolean;
  window_size: number;
  sensitivity: number;
  params: Record<string, unknown>;
}

export interface DetectorConfig {
  metric_name: string;
  ensemble_mode: 'majority' | 'weighted' | 'any';
  zscore: DetectorSettings;
  ewma: DetectorSettings;
  isolation_forest: DetectorSettings;
  percentile: DetectorSettings;
  updated_at?: number;
}

export interface MetricSummary {
  name: string;
  last_value: number;
  mean: number;
  stddev: number;
  min_value?: number;
  max_value?: number;
  point_count?: number;
  anomaly_count: number;
  last_timestamp?: number;
}

export interface HealthData {
  status: string;
  db: string;
  queue_depth: number;
  ws_clients: number;
  simulator_running: boolean;
}

export interface SimulatorConfig {
  scenario: string;
  rate_per_second: number;
  metrics: string[];
}

// ── API Response ──

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: Record<string, unknown>;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

// ── WebSocket Messages ──

export type WsEventType =
  | 'metric_point'
  | 'anomaly_detected'
  | 'alert_triggered'
  | 'alert_resolved'
  | 'system_status'
  | 'simulator_status';

export interface WsMessage<T = unknown> {
  type: WsEventType;
  version: number;
  payload: T;
}

export interface WsSubscription {
  type: 'subscribe';
  payload: {
    metrics?: string[];
    events?: WsEventType[];
  };
}
