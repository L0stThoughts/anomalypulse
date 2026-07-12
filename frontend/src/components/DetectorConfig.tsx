import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { getDetectorConfig, updateDetectorConfig } from '../lib/api';
import type { DetectorConfig, DetectorSettings } from '../types';

const DETECTORS = ['zscore', 'ewma', 'isolation_forest', 'percentile'] as const;
type DetectorKey = (typeof DETECTORS)[number];

const LABELS: Record<DetectorKey, string> = {
  zscore: 'Z-Score',
  ewma: 'EWMA',
  isolation_forest: 'Isolation Forest',
  percentile: 'Percentile',
};

function DetectorSlider({
  label,
  settings,
  onChange,
}: {
  label: string;
  settings: DetectorSettings;
  onChange: (s: DetectorSettings) => void;
}) {
  return (
    <div className="p-3 rounded bg-slate-700/30 border border-slate-600/50 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-200">{label}</span>
        <button
          onClick={() => onChange({ ...settings, enabled: !settings.enabled })}
          className={`text-[10px] px-2 py-0.5 rounded ${
            settings.enabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-600 text-slate-400'
          }`}
        >
          {settings.enabled ? 'ON' : 'OFF'}
        </button>
      </div>
      {settings.enabled && (
        <>
          <label className="flex items-center justify-between text-[10px] text-slate-400">
            <span>Window Size</span>
            <span className="font-mono text-slate-300">{settings.window_size}</span>
          </label>
          <input
            type="range"
            min={10}
            max={300}
            step={10}
            value={settings.window_size}
            onChange={(e) => onChange({ ...settings, window_size: +e.target.value })}
            className="w-full h-1 bg-slate-600 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
          <label className="flex items-center justify-between text-[10px] text-slate-400">
            <span>Sensitivity</span>
            <span className="font-mono text-slate-300">{settings.sensitivity.toFixed(2)}</span>
          </label>
          <input
            type="range"
            min={0.1}
            max={5}
            step={0.1}
            value={settings.sensitivity}
            onChange={(e) => onChange({ ...settings, sensitivity: +e.target.value })}
            className="w-full h-1 bg-slate-600 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </>
      )}
    </div>
  );
}

export function DetectorConfigPanel() {
  const selectedMetric = useAppStore((s) => s.selectedMetric);
  const [config, setConfig] = useState<DetectorConfig | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!selectedMetric) return;
    getDetectorConfig(selectedMetric).then(setConfig).catch(() => setConfig(null));
  }, [selectedMetric]);

  if (!selectedMetric) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <p className="text-xs text-slate-500">Select a metric to configure detectors.</p>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <p className="text-xs text-slate-500">Loading detector config...</p>
      </div>
    );
  }

  const handleUpdate = (key: DetectorKey, settings: DetectorSettings) => {
    setConfig({ ...config, [key]: settings });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateDetectorConfig(selectedMetric, config);
    } catch { /* ignored */ }
    setSaving(false);
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Detector Config</h2>
        <div className="flex items-center gap-2">
          <select
            className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-xs text-slate-200"
            value={config.ensemble_mode}
            onChange={(e) =>
              setConfig({ ...config, ensemble_mode: e.target.value as DetectorConfig['ensemble_mode'] })
            }
          >
            <option value="majority">Majority</option>
            <option value="weighted">Weighted</option>
            <option value="any">Any</option>
          </select>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {DETECTORS.map((key) => (
          <DetectorSlider
            key={key}
            label={LABELS[key]}
            settings={config[key]}
            onChange={(s) => handleUpdate(key, s)}
          />
        ))}
      </div>
    </div>
  );
}
