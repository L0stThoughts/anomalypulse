import { create } from 'zustand';
import type { MetricPoint, MetricSummary, AnomalyEvent } from '../types';

const MAX_POINTS = 500;

interface MetricsState {
  summaries: MetricSummary[];
  points: Record<string, MetricPoint[]>;
  anomalies: AnomalyEvent[];

  setMetrics: (summaries: MetricSummary[]) => void;
  addPoint: (point: MetricPoint) => void;
  addAnomaly: (anomaly: AnomalyEvent) => void;
  setAnomalies: (anomalies: AnomalyEvent[]) => void;
  setPoints: (metric: string, pts: MetricPoint[]) => void;
}

export const useMetricsStore = create<MetricsState>((set) => ({
  summaries: [],
  points: {},
  anomalies: [],

  setMetrics: (summaries) => set({ summaries }),

  addPoint: (point) =>
    set((s) => {
      const key = point.metric_name;
      const existing = s.points[key] ?? [];
      const updated = [...existing, point].slice(-MAX_POINTS);
      return { points: { ...s.points, [key]: updated } };
    }),

  addAnomaly: (anomaly) =>
    set((s) => ({
      anomalies: [...s.anomalies, anomaly].slice(-200),
    })),

  setAnomalies: (anomalies) => set({ anomalies }),

  setPoints: (metric, pts) =>
    set((s) => ({ points: { ...s.points, [metric]: pts.slice(-MAX_POINTS) } })),
}));
