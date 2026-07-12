import { create } from 'zustand';
import type { HealthData } from '../types';

type TimeRange = '1m' | '5m' | '15m' | '30m' | '1h';

interface AppState {
  wsConnected: boolean;
  simulatorRunning: boolean;
  health: HealthData | null;
  selectedMetric: string | null;
  timeRange: TimeRange;
  activeTab: 'chart' | 'anomalies' | 'alerts' | 'detectors';

  setWsConnected: (v: boolean) => void;
  setSimulatorRunning: (v: boolean) => void;
  setHealth: (h: HealthData) => void;
  setSelectedMetric: (m: string | null) => void;
  setTimeRange: (r: TimeRange) => void;
  setActiveTab: (t: AppState['activeTab']) => void;
}

export const useAppStore = create<AppState>((set) => ({
  wsConnected: false,
  simulatorRunning: false,
  health: null,
  selectedMetric: null,
  timeRange: '5m',
  activeTab: 'chart',

  setWsConnected: (v) => set({ wsConnected: v }),
  setSimulatorRunning: (v) => set({ simulatorRunning: v }),
  setHealth: (h) => set({ health: h }),
  setSelectedMetric: (m) => set({ selectedMetric: m }),
  setTimeRange: (r) => set({ timeRange: r }),
  setActiveTab: (t) => set({ activeTab: t }),
}));
