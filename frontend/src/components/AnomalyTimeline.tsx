import { useMetricsStore } from '../stores/metricsStore';

const SEVERITY_STYLES: Record<string, { dot: string; border: string; text: string }> = {
  critical: { dot: 'bg-red-500', border: 'border-red-500/30', text: 'text-red-400' },
  warning: { dot: 'bg-amber-500', border: 'border-amber-500/30', text: 'text-amber-400' },
  info: { dot: 'bg-blue-500', border: 'border-blue-500/30', text: 'text-blue-400' },
};

export function AnomalyTimeline() {
  const anomalies = useMetricsStore((s) => s.anomalies);
  const recent = anomalies.slice(-50).reverse();

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <h2 className="text-sm font-semibold text-slate-200 mb-3">Anomaly Timeline</h2>
      {recent.length === 0 ? (
        <p className="text-xs text-slate-500">No anomalies detected yet.</p>
      ) : (
        <div className="space-y-1 max-h-96 overflow-y-auto pr-1">
          {recent.map((a, i) => {
            const s = SEVERITY_STYLES[a.severity] ?? SEVERITY_STYLES.info;
            return (
              <div
                key={`${a.metric}-${a.timestamp}-${i}`}
                className={`flex items-start gap-3 p-2 rounded border ${s.border} bg-slate-800/50`}
              >
                <div className="flex flex-col items-center pt-1">
                  <span className={`w-2 h-2 rounded-full ${s.dot} ${a.severity === 'critical' ? 'animate-pulse' : ''}`} />
                  {i < recent.length - 1 && <span className="w-px flex-1 bg-slate-700 mt-1" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-300 truncate">{a.metric}</span>
                    <span className={`text-[10px] font-medium uppercase ${s.text}`}>{a.severity}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Score: {a.score.toFixed(3)} · {a.detector} · {new Date(a.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
