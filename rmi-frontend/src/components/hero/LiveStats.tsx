/**
 * LiveStats — Real-time animated counters on the landing page
 * Data from /api/v1/stats, refreshes every 15s
 */
import { Shield, Activity, Users, Radio } from 'lucide-react';
import CountUp from '../CountUp';
import { useLiveStats } from '../../hooks/useLiveStats';

export default function LiveStats() {
  const stats = useLiveStats(15000);

  const items = [
    { label: 'Scams Detected', value: stats.scams_detected, icon: Shield, color: 'text-red-400' },
    { label: 'Scans Today', value: stats.scans_today, icon: Activity, color: 'text-purple-400' },
    { label: 'Active Alerts', value: stats.alerts_active, icon: Radio, color: 'text-yellow-400' },
    { label: 'Active Users', value: stats.active_users, icon: Users, color: 'text-emerald-400' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div key={item.label} className="glass-card rounded-xl p-4 text-center transition-all duration-300 hover:scale-[1.02]">
            <Icon className={`w-5 h-5 mx-auto mb-2 ${item.color}`} />
            <div className={`text-2xl sm:text-3xl font-bold tabular-nums ${item.color}`}>
              {stats.loading && item.value === 0 ? (
                <span className="text-slate-700 text-lg">---</span>
              ) : (
                <CountUp value={item.value} duration={1500} />
              )}
            </div>
            <div className="text-xs text-slate-500 mt-1">{item.label}</div>
          </div>
        );
      })}
    </div>
  );
}
