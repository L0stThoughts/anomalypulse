import { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot,
} from 'recharts';
import { useMetricsStore } from '../stores/metricsStore';
import { useAppStore } from '../stores/appStore';

export function MetricChart() {
  const selectedMetric = useAppStore((s) => s.selectedMetric);
  const points = useMetricsStore((s) => (selectedMetric ? s.points[selectedMetric] ?? [] : []));
  const anomalies = useMetricsStore((s) => s.anomalies);

  const metricAnomalies = useMemo(
    () => anomalies.filter((a) => a.metric === selectedMetric),
    [anomalies, selectedMetric],
  );

  const chartData = useMemo(
    () =>
      points.map((p) => ({
        time: p.timestamp,
        value: p.value,
        label: new Date(p.timestamp).toLocaleTimeString(),
      })),
    [points],
  );

  const anomalyDots = useMemo(
    () =>
      metricAnomalies
        .map((a) => {
          const pt = points.find((p) => p.timestamp === a.timestamp);
          if (!pt) return null;
          return { time: pt.timestamp, value: pt.value, severity: a.severity, score: a.score };
        })
        .filter(Boolean) as { time: number; value: number; severity: string; score: number }[],
    [metricAnomalies, points],
  );

  if (!selectedMetric) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-8 flex items-center justify-center h-80">
        <p className="text-slate-500 text-sm">Select a metric from the sidebar</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold font-mono text-slate-200">{selectedMetric}</h2>
        <span className="text-[10px] text-slate-500">{points.length} points</span>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="label"
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickLine={{ stroke: '#475569' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickLine={{ stroke: '#475569' }}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 6,
              fontSize: 12,
            }}
            labelStyle={{ color: '#94a3b8' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#34d399"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          {anomalyDots.map((d, i) => (
            <ReferenceDot
              key={i}
              x={new Date(d.time).toLocaleTimeString()}
              y={d.value}
              r={5}
              fill={d.severity === 'critical' ? '#ef4444' : d.severity === 'warning' ? '#f59e0b' : '#3b82f6'}
              stroke="none"
              className="animate-pulse"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
