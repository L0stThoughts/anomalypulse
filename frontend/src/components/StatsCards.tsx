import { useMetricsStore } from '../stores/metricsStore';
import { useAlertStore } from '../stores/alertStore';

export function StatsCards() {
  const summaries = useMetricsStore((s) => s.summaries);
  const anomalies = useMetricsStore((s) => s.anomalies);
  const alerts = useAlertStore((s) => s.alerts);

  const totalPoints = summaries.reduce((sum, m) => sum + (m.point_count ?? 0), 0);
  const totalAnomalies = anomalies.length;
  const openAlerts = alerts.filter((a) => a.status === 'open').length;
  const detectionRate = totalPoints > 0 ? ((totalAnomalies / totalPoints) * 100).toFixed(2) : '0.00';

  const cards = [
    { label: 'Active Metrics', value: summaries.length, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Anomalies', value: totalAnomalies, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { label: 'Open Alerts', value: openAlerts, color: 'text-red-400', bg: 'bg-red-500/10' },
    { label: 'Detection Rate', value: `${detectionRate}%`, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className={`${c.bg} rounded-lg border border-slate-700 p-3`}
        >
          <p className="text-[10px] uppercase tracking-wider text-slate-500">{c.label}</p>
          <p className={`text-2xl font-bold tabular-nums ${c.color} mt-1`}>{c.value}</p>
        </div>
      ))}
    </div>
  );
}
