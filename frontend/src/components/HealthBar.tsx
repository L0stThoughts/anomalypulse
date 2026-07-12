import { useAppStore } from '../stores/appStore';

export function HealthBar() {
  const health = useAppStore((s) => s.health);
  const wsConnected = useAppStore((s) => s.wsConnected);

  const items = [
    {
      label: 'WebSocket',
      ok: wsConnected,
      detail: wsConnected ? 'Connected' : 'Disconnected',
    },
    {
      label: 'Database',
      ok: health?.db === 'ok',
      detail: health?.db ?? '—',
    },
    {
      label: 'Queue',
      ok: health ? health.queue_depth < 5000 : false,
      detail: health ? String(health.queue_depth) : '—',
    },
    {
      label: 'WS Clients',
      ok: true,
      detail: health ? String(health.ws_clients) : '—',
    },
    {
      label: 'Simulator',
      ok: health?.simulator_running ?? false,
      detail: health?.simulator_running ? 'Running' : 'Stopped',
    },
  ];

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-slate-800 border-b border-slate-700 text-[11px]">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              item.ok ? 'bg-emerald-400' : 'bg-red-400'
            }`}
          />
          <span className="text-slate-400">{item.label}:</span>
          <span className={item.ok ? 'text-slate-300' : 'text-red-400'}>{item.detail}</span>
        </div>
      ))}
    </div>
  );
}
