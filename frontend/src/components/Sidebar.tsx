import { useMetricsStore } from '../stores/metricsStore';
import { useAppStore } from '../stores/appStore';
import { startSimulator, stopSimulator } from '../lib/api';
import { useState } from 'react';

export function Sidebar() {
  const summaries = useMetricsStore((s) => s.summaries);
  const selectedMetric = useAppStore((s) => s.selectedMetric);
  const setSelectedMetric = useAppStore((s) => s.setSelectedMetric);
  const simulatorRunning = useAppStore((s) => s.simulatorRunning);
  const setSimulatorRunning = useAppStore((s) => s.setSimulatorRunning);
  const [simLoading, setSimLoading] = useState(false);

  const toggleSimulator = async () => {
    setSimLoading(true);
    try {
      if (simulatorRunning) {
        await stopSimulator();
        setSimulatorRunning(false);
      } else {
        await startSimulator({ scenario: 'cpu_spike', rate_per_second: 4, metrics: ['cpu.usage', 'memory.usage', 'disk.io', 'network.rx'] });
        setSimulatorRunning(true);
      }
    } catch { /* ignored */ }
    setSimLoading(false);
  };

  return (
    <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-lg font-bold tracking-tight">
          <span className="text-emerald-400">◈</span> AnomalyPulse
        </h1>
        <p className="text-xs text-slate-400 mt-1">Real-time Anomaly Detection</p>
      </div>

      {/* Simulator Control */}
      <div className="p-3 border-b border-slate-700">
        <button
          onClick={toggleSimulator}
          disabled={simLoading}
          className={`w-full px-3 py-2 rounded text-sm font-medium transition-colors ${
            simulatorRunning
              ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/40'
              : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/40'
          } disabled:opacity-50`}
        >
          {simLoading ? '...' : simulatorRunning ? '■ Stop Simulator' : '▶ Start Simulator'}
        </button>
      </div>

      {/* Metrics List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <p className="text-[10px] uppercase tracking-wider text-slate-500 px-2 py-1">
          Metrics ({summaries.length})
        </p>
        {summaries.length === 0 && (
          <p className="text-xs text-slate-500 px-2">No metrics yet. Start the simulator.</p>
        )}
        {summaries.map((m) => {
          const isSelected = selectedMetric === m.name;
          return (
            <button
              key={m.name}
              onClick={() => setSelectedMetric(m.name)}
              className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                isSelected
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-300 hover:bg-slate-700/50'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs truncate">{m.name}</span>
                {m.anomaly_count > 0 && (
                  <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded-full bg-red-500/20 text-red-400 font-medium tabular-nums animate-pulse">
                    {m.anomaly_count}
                  </span>
                )}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                {m.last_value.toFixed(2)} · μ {m.mean.toFixed(1)} · σ {m.stddev.toFixed(1)}
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
