import { useEffect, useRef } from 'react';
import { dashboardWs } from '../lib/websocket';
import { useMetricsStore } from '../stores/metricsStore';
import { useAlertStore } from '../stores/alertStore';
import { useAppStore } from '../stores/appStore';
import type { WsMessage, MetricPoint, AnomalyEvent, AlertEvent, HealthData } from '../types';

export function useWebSocket() {
  const started = useRef(false);
  const addPoint = useMetricsStore((s) => s.addPoint);
  const addAnomaly = useMetricsStore((s) => s.addAnomaly);
  const addAlert = useAlertStore((s) => s.addAlert);
  const setWsConnected = useAppStore((s) => s.setWsConnected);
  const setHealth = useAppStore((s) => s.setHealth);
  const setSimulatorRunning = useAppStore((s) => s.setSimulatorRunning);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const unsub = dashboardWs.subscribe((msg: WsMessage) => {
      switch (msg.type) {
        case 'metric_point':
          addPoint(msg.payload as MetricPoint);
          break;
        case 'anomaly_detected':
          addAnomaly(msg.payload as AnomalyEvent);
          break;
        case 'alert_triggered':
          addAlert(msg.payload as AlertEvent);
          break;
        case 'system_status':
          setHealth(msg.payload as HealthData);
          break;
        case 'simulator_status':
          setSimulatorRunning((msg.payload as { running: boolean }).running);
          break;
      }
    });

    // Track connection state
    const interval = setInterval(() => {
      setWsConnected(dashboardWs.connected);
    }, 1000);

    dashboardWs.connect();

    return () => {
      unsub();
      clearInterval(interval);
      dashboardWs.dispose();
    };
  }, [addPoint, addAnomaly, addAlert, setWsConnected, setHealth, setSimulatorRunning]);
}
