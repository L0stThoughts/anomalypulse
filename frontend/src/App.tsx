import { useEffect } from 'react';
import { Layout } from './components/Layout';
import { StatsCards } from './components/StatsCards';
import { MetricChart } from './components/MetricChart';
import { AnomalyTimeline } from './components/AnomalyTimeline';
import { AlertPanel } from './components/AlertPanel';
import { DetectorConfigPanel } from './components/DetectorConfig';
import { useWebSocket } from './hooks/useWebSocket';
import { useAppStore } from './stores/appStore';
import { useMetricsStore } from './stores/metricsStore';
import { useAlertStore } from './stores/alertStore';
import { getMetrics, getAnomalies, getAlerts, getAlertRules, getHealth } from './lib/api';

function Dashboard() {
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);

  const tabs = [
    { key: 'chart' as const, label: 'Chart' },
    { key: 'anomalies' as const, label: 'Anomalies' },
    { key: 'alerts' as const, label: 'Alerts' },
    { key: 'detectors' as const, label: 'Detectors' },
  ];

  return (
    <>
      <StatsCards />
      <div className="flex gap-1 border-b border-slate-700 pb-0">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-3 py-1.5 text-xs font-medium transition-colors rounded-t ${
              activeTab === t.key
                ? 'bg-slate-800 text-emerald-400 border border-slate-700 border-b-slate-800 -mb-px'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {activeTab === 'chart' && <MetricChart />}
      {activeTab === 'anomalies' && <AnomalyTimeline />}
      {activeTab === 'alerts' && <AlertPanel />}
      {activeTab === 'detectors' && <DetectorConfigPanel />}
    </>
  );
}

export default function App() {
  useWebSocket();

  const setMetrics = useMetricsStore((s) => s.setMetrics);
  const setAnomalies = useMetricsStore((s) => s.setAnomalies);
  const setAlerts = useAlertStore((s) => s.setAlerts);
  const setRules = useAlertStore((s) => s.setRules);
  const setHealth = useAppStore((s) => s.setHealth);
  const setSelectedMetric = useAppStore((s) => s.setSelectedMetric);

  useEffect(() => {
    const load = async () => {
      try {
        const [metrics, anomalies, alerts, rules, health] = await Promise.allSettled([
          getMetrics(),
          getAnomalies({ limit: 100 }),
          getAlerts({ limit: 100 }),
          getAlertRules(),
          getHealth(),
        ]);
        if (metrics.status === 'fulfilled') {
          setMetrics(metrics.value);
          if (metrics.value.length > 0) setSelectedMetric(metrics.value[0].name);
        }
        if (anomalies.status === 'fulfilled') setAnomalies(anomalies.value);
        if (alerts.status === 'fulfilled') setAlerts(alerts.value);
        if (rules.status === 'fulfilled') setRules(rules.value);
        if (health.status === 'fulfilled') setHealth(health.value);
      } catch { /* initial load best-effort */ }
    };
    load();

    // Refresh metrics summaries every 5s
    const interval = setInterval(async () => {
      try {
        const m = await getMetrics();
        setMetrics(m);
      } catch { /* ignore */ }
    }, 5000);

    return () => clearInterval(interval);
  }, [setMetrics, setAnomalies, setAlerts, setRules, setHealth, setSelectedMetric]);

  return (
    <Layout>
      <Dashboard />
    </Layout>
  );
}
