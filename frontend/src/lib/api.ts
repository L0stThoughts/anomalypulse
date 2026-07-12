import type {
  ApiResponse,
  MetricSummary,
  MetricPoint,
  AnomalyEvent,
  AlertEvent,
  AlertRule,
  DetectorConfig,
  HealthData,
  SimulatorConfig,
} from '../types';

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8080';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  const json: ApiResponse<T> = await res.json();
  if (!json.success) throw new Error('Request failed');
  return json.data;
}

// ── Health ──
export const getHealth = () => request<HealthData>('/api/v1/health');

// ── Metrics ──
export const getMetrics = () => request<MetricSummary[]>('/api/v1/metrics');

export const getMetricLatest = (metric: string) =>
  request<{ point: MetricPoint; latest_anomaly: { score: number; severity: string } | null }>(
    `/api/v1/metrics/${encodeURIComponent(metric)}/latest`,
  );

export const getMetricHistory = (
  metric: string,
  params?: { start?: number; end?: number; limit?: number },
) => {
  const q = new URLSearchParams();
  if (params?.start) q.set('start', String(params.start));
  if (params?.end) q.set('end', String(params.end));
  if (params?.limit) q.set('limit', String(params.limit));
  return request<{ metric_name: string; points: MetricPoint[] }>(
    `/api/v1/metrics/${encodeURIComponent(metric)}/history?${q}`,
  );
};

// ── Anomalies ──
export const getAnomalies = (params?: {
  metric?: string;
  severity?: string;
  start?: number;
  end?: number;
  limit?: number;
}) => {
  const q = new URLSearchParams();
  if (params?.metric) q.set('metric', params.metric);
  if (params?.severity) q.set('severity', params.severity);
  if (params?.start) q.set('start', String(params.start));
  if (params?.end) q.set('end', String(params.end));
  if (params?.limit) q.set('limit', String(params.limit));
  return request<AnomalyEvent[]>(`/api/v1/anomalies?${q}`);
};

// ── Alerts ──
export const getAlerts = (params?: { status?: string; severity?: string; metric?: string; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.status) q.set('status', params.status);
  if (params?.severity) q.set('severity', params.severity);
  if (params?.metric) q.set('metric', params.metric);
  if (params?.limit) q.set('limit', String(params.limit));
  return request<AlertEvent[]>(`/api/v1/alerts?${q}`);
};

// ── Alert Rules ──
export const getAlertRules = () => request<AlertRule[]>('/api/v1/alert-rules');

export const createAlertRule = (rule: Partial<AlertRule>) =>
  request<{ id: string; created: boolean }>('/api/v1/alert-rules', {
    method: 'POST',
    body: JSON.stringify(rule),
  });

export const updateAlertRule = (id: string, patch: Partial<AlertRule>) =>
  request<{ id: string; updated: boolean }>(`/api/v1/alert-rules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(patch),
  });

export const deleteAlertRule = (id: string) =>
  request<{ id: string; deleted: boolean }>(`/api/v1/alert-rules/${id}`, {
    method: 'DELETE',
  });

// ── Detectors ──
export const getDetectorConfig = (metric: string) =>
  request<DetectorConfig>(`/api/v1/detectors/${encodeURIComponent(metric)}`);

export const updateDetectorConfig = (metric: string, config: Partial<DetectorConfig>) =>
  request<{ metric_name: string; updated: boolean }>(
    `/api/v1/detectors/${encodeURIComponent(metric)}`,
    { method: 'PUT', body: JSON.stringify(config) },
  );

// ── Simulator ──
export const startSimulator = (config?: Partial<SimulatorConfig>) =>
  request<{ running: boolean; scenario: string }>('/api/v1/simulator/start', {
    method: 'POST',
    body: JSON.stringify(config ?? {}),
  });

export const stopSimulator = () =>
  request<{ running: boolean }>('/api/v1/simulator/stop', { method: 'POST' });
