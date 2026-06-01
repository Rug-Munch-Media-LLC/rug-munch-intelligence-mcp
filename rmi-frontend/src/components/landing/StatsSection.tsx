/**
 * StatsSection — Real-time platform stats with animated counters
 * Data from /api/v1/stats (refreshes every 15s)
 */
import { Shield, Activity, Radio, Users, Zap } from 'lucide-react';
import ScrollReveal from '../hero/ScrollReveal';
import CountUp from '../CountUp';
import { useLiveStats } from '../../hooks/useLiveStats';

const STAT_ITEMS = [
  { key: 'scams_detected', label: 'Scams Detected', icon: Shield, color: 'text-red-400', bgColor: 'bg-red-500/10', borderColor: 'border-red-500/20' },
  { key: 'scans_today', label: 'Scans Today', icon: Activity, color: 'text-purple-400', bgColor: 'bg-purple-500/10', borderColor: 'border-purple-500/20' },
  { key: 'alerts_active', label: 'Active Alerts', icon: Radio, color: 'text-yellow-400', bgColor: 'bg-yellow-500/10', borderColor: 'border-yellow-500/20' },
  { key: 'active_users', label: 'Active Users', icon: Users, color: 'text-emerald-400', bgColor: 'bg-emerald-500/10', borderColor: 'border-emerald-500/20' },
];

export default function StatsSection() {
  const stats = useLiveStats(15000);

  return (
    <section className="relative py-16 border-y border-purple-500/10 bg-gradient-to-r from-purple-950/20 via-slate-950 to-purple-950/20">
      {/* Subtle scan line effect */}
      <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(168,85,247,0.01)_2px,rgba(168,85,247,0.01)_4px)] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ScrollReveal direction="up" distance={20}>
          <div className="flex items-center justify-center gap-2 mb-8">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-mono text-emerald-400/80 tracking-widest uppercase">Live Data</span>
            <span className="text-xs text-slate-600">
              {stats.last_updated ? new Date(stats.last_updated).toLocaleTimeString() : ''}
            </span>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {STAT_ITEMS.map((item) => {
              const Icon = item.icon;
              const value = (stats as any)[item.key] ?? 0;
              return (
                <div key={item.key} className={`relative group ${item.bgColor} ${item.borderColor} border rounded-xl p-5 backdrop-blur-sm transition-all duration-300 hover:scale-[1.02] hover:border-opacity-50`}>
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`p-2 rounded-lg ${item.bgColor} ${item.borderColor} border`}>
                      <Icon className={`w-5 h-5 ${item.color}`} />
                    </div>
                    <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">{item.label}</span>
                  </div>
                  <div className={`text-3xl sm:text-4xl font-bold ${item.color} tabular-nums`}>
                    {stats.loading && value === 0 ? (
                      <span className="text-slate-700 animate-pulse">---</span>
                    ) : (
                      <CountUp value={value} duration={1200} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
