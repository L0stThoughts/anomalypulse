import { useAlertStore } from '../stores/alertStore';
import { useState } from 'react';
import { createAlertRule, deleteAlertRule } from '../lib/api';

const SEV_COLOR: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/10',
  warning: 'text-amber-400 bg-amber-500/10',
  info: 'text-blue-400 bg-blue-500/10',
};

export function AlertPanel() {
  const alerts = useAlertStore((s) => s.alerts);
  const rules = useAlertStore((s) => s.rules);
  const setRules = useAlertStore((s) => s.setRules);
  const removeRule = useAlertStore((s) => s.removeRule);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '',
    metric_pattern: '',
    severity: 'warning' as 'info' | 'warning' | 'critical',
    score_threshold: 0.8,
    cooldown: 300,
  });

  const handleCreate = async () => {
    try {
      const res = await createAlertRule({
        name: form.name,
        metric_pattern: form.metric_pattern,
        rule_type: 'anomaly_score',
        severity: form.severity,
        thresholds: { score_gte: form.score_threshold },
        cooldown_seconds: form.cooldown,
        actions: ['dashboard'],
      });
      setRules([
        ...rules,
        {
          id: res.id,
          name: form.name,
          enabled: true,
          metric_pattern: form.metric_pattern,
          rule_type: 'anomaly_score',
          detector_config: {},
          thresholds: { score_gte: form.score_threshold },
          severity: form.severity,
          cooldown_seconds: form.cooldown,
          actions: ['dashboard'],
          filters: {},
        },
      ]);
      setShowForm(false);
      setForm({ name: '', metric_pattern: '', severity: 'warning', score_threshold: 0.8, cooldown: 300 });
    } catch { /* ignored */ }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAlertRule(id);
      removeRule(id);
    } catch { /* ignored */ }
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 space-y-4">
      {/* Active Alerts */}
      <div>
        <h2 className="text-sm font-semibold text-slate-200 mb-2">Active Alerts</h2>
        {alerts.length === 0 ? (
          <p className="text-xs text-slate-500">No alerts triggered.</p>
        ) : (
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {alerts.slice(0, 50).map((a) => (
              <div
                key={a.id}
                className={`flex items-center justify-between px-3 py-2 rounded text-xs ${SEV_COLOR[a.severity] ?? ''}`}
              >
                <div>
                  <span className="font-medium">{a.message}</span>
                  <span className="ml-2 text-slate-500 font-mono">{a.metric}</span>
                </div>
                <span className="text-slate-500 tabular-nums">{new Date(a.triggered_at).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Alert Rules */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-slate-200">Alert Rules</h2>
          <button
            onClick={() => setShowForm(!showForm)}
            className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
          >
            {showForm ? 'Cancel' : '+ New Rule'}
          </button>
        </div>

        {showForm && (
          <div className="space-y-2 p-3 rounded bg-slate-700/50 border border-slate-600 mb-3">
            <input
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              placeholder="Rule name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
            <input
              className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              placeholder="Metric pattern (e.g. cpu.*)"
              value={form.metric_pattern}
              onChange={(e) => setForm((f) => ({ ...f, metric_pattern: e.target.value }))}
            />
            <div className="flex gap-2">
              <select
                className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none"
                value={form.severity}
                onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value as 'info' | 'warning' | 'critical' }))}
              >
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
              <label className="flex items-center gap-1 text-xs text-slate-400">
                Score ≥
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  className="w-16 bg-slate-700 border border-slate-600 rounded px-1 py-1 text-xs text-slate-200"
                  value={form.score_threshold}
                  onChange={(e) => setForm((f) => ({ ...f, score_threshold: +e.target.value }))}
                />
              </label>
            </div>
            <button
              onClick={handleCreate}
              className="px-3 py-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded transition-colors"
            >
              Create Rule
            </button>
          </div>
        )}

        {rules.length === 0 && !showForm && (
          <p className="text-xs text-slate-500">No rules configured.</p>
        )}
        <div className="space-y-1">
          {rules.map((r) => (
            <div key={r.id} className="flex items-center justify-between px-3 py-2 rounded bg-slate-700/30 text-xs">
              <div>
                <span className="text-slate-200 font-medium">{r.name}</span>
                <span className="ml-2 font-mono text-slate-500">{r.metric_pattern}</span>
                <span className={`ml-2 uppercase text-[10px] ${SEV_COLOR[r.severity]?.split(' ')[0] ?? 'text-slate-400'}`}>
                  {r.severity}
                </span>
              </div>
              <button
                onClick={() => handleDelete(r.id)}
                className="text-slate-500 hover:text-red-400 transition-colors"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
