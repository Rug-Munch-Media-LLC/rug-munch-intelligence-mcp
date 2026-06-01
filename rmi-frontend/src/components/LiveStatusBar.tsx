/**
 * LiveStatusBar — Sticky top bar with real-time platform counters
 * Shows: scans today, active alerts, scams detected, chains monitored
 * Data from /api/v1/stats (refreshes every 15s)
 */
import { useState, useEffect } from 'react';
import { Shield, Activity, Radio, Globe, Zap } from 'lucide-react';
import api from '../services/api';

interface BarStats {
  scans_today: number;
  alerts_active: number;
  scams_detected: number;
  chains: number;
}

export default function LiveStatusBar() {
  const [stats, setStats] = useState<BarStats>({ scans_today: 0, alerts_active: 0, scams_detected: 0, chains: 8 });
  const [pulse, setPulse] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const [ps, ac] = await Promise.allSettled([
          api.client.get('/api/v1/stats').then(r => r.data).catch(() => ({})),
          api.client.get('/api/v1/alerts/count').then(r => r.data).catch(() => ({})),
        ]);
        const platformStats = ps.status === 'fulfilled' ? ps.value : {};
        const alertCount = ac.status === 'fulfilled' ? ac.value : {};
        setStats({
          scans_today: platformStats?.scans_today ?? platformStats?.api_calls_today ?? 0,
          alerts_active: alertCount?.count ?? alertCount?.active_alerts ?? 0,
          scams_detected: alertCount?.scams_detected ?? alertCount?.total_scams ?? 0,
          chains: 8,
        });
        setPulse(prev => !prev); // toggle to refresh pulse animation
      } catch {}
    };
    fetch();
    const interval = setInterval(fetch, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="hidden lg:block sticky top-0 z-50 bg-[#08080f]/95 backdrop-blur-xl border-b border-purple-500/15">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${pulse ? 'bg-emerald-400' : 'bg-emerald-600'} transition-colors duration-1000`} />
              <span className="text-slate-500 font-mono tracking-wider">RMI LIVE</span>
            </div>
            <Stat label="Scans Today" value={stats.scans_today} icon={Activity} color="text-purple-400" />
            <Stat label="Active Alerts" value={stats.alerts_active} icon={Radio} color="text-yellow-400" />
            <Stat label="Scams Detected" value={stats.scams_detected} icon={Shield} color="text-red-400" />
          </div>
          <div className="flex items-center gap-6">
            <Stat label="Chains" value={stats.chains} icon={Globe} color="text-emerald-400" />
            <span className="text-slate-600 font-mono text-[10px]">
              {stats.scans_today > 0 ? `${stats.scans_today.toLocaleString()} scans` : 'Monitoring...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, icon: Icon, color }: { label: string; value: number; icon: any; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon className={`w-3 h-3 ${color}`} />
      <span className="text-slate-500">{label}</span>
      <span className={`font-bold tabular-nums ${color}`}>{value > 0 ? value.toLocaleString() : '--'}</span>
    </div>
  );
}
