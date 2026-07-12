import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { HealthBar } from './HealthBar';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <HealthBar />
        <main className="flex-1 overflow-auto p-4 space-y-4">{children}</main>
      </div>
    </div>
  );
}
