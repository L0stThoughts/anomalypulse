import { create } from 'zustand';
import type { AlertEvent, AlertRule } from '../types';

interface AlertState {
  alerts: AlertEvent[];
  rules: AlertRule[];

  addAlert: (alert: AlertEvent) => void;
  setAlerts: (alerts: AlertEvent[]) => void;
  setRules: (rules: AlertRule[]) => void;
  updateRule: (id: string, patch: Partial<AlertRule>) => void;
  removeRule: (id: string) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  rules: [],

  addAlert: (alert) =>
    set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 200) })),

  setAlerts: (alerts) => set({ alerts }),
  setRules: (rules) => set({ rules }),

  updateRule: (id, patch) =>
    set((s) => ({
      rules: s.rules.map((r) => (r.id === id ? { ...r, ...patch } : r)),
    })),

  removeRule: (id) =>
    set((s) => ({ rules: s.rules.filter((r) => r.id !== id) })),
}));
