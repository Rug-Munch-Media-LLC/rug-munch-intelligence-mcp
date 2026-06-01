/**
 * useLiveStats — Polls /api/v1/stats and /api/v1/alerts/count for real-time platform numbers
 */
import { useState, useEffect, useRef } from 'react';
import api from '../services/api';

export interface LiveStats {
  scans_today: number;
  total_scans: number;
  alerts_active: number;
  scams_detected: number;
  active_users: number;
  cache_hit_rate: number;
  rag_collections: number;
  api_calls_today: number;
  last_updated: string;
  loading: boolean;
}

export function useLiveStats(pollIntervalMs: number = 15000): LiveStats {
  const [stats, setStats] = useState<LiveStats>({
    scans_today: 0, total_scans: 0, alerts_active: 0, scams_detected: 0,
    active_users: 0, cache_hit_rate: 0, rag_collections: 0, api_calls_today: 0,
    last_updated: '', loading: true,
  });
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const fetchStats = async () => {
      try {
        const [platformStats, alertCount] = await Promise.allSettled([
          api.client.get('/api/v1/stats').then(r => r.data).catch(() => null),
          api.client.get('/api/v1/alerts/count').then(r => r.data).catch(() => null),
        ]);
        if (!mounted.current) return;
        const ps = platformStats.status === 'fulfilled' ? platformStats.value : {};
        const ac = alertCount.status === 'fulfilled' ? alertCount.value : {};
        setStats({
          scans_today: ps?.scans_today ?? ps?.api_calls_today ?? 0,
          total_scans: ps?.total_scans ?? ps?.total_investigations ?? 0,
          alerts_active: ac?.count ?? ac?.active_alerts ?? 0,
          scams_detected: ac?.scams_detected ?? ac?.total_scams ?? 0,
          active_users: ps?.active_users ?? ps?.total_users ?? 0,
          cache_hit_rate: ps?.cache_hit_rate ?? ps?.rmi_redis_hit_rate ?? 0,
          rag_collections: ps?.rag_collections ?? ps?.collections ?? 0,
          api_calls_today: ps?.api_calls_today ?? 0,
          last_updated: new Date().toISOString(),
          loading: false,
        });
      } catch {
        if (mounted.current) setStats(prev => ({ ...prev, loading: false }));
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, pollIntervalMs);
    return () => { mounted.current = false; clearInterval(interval); };
  }, [pollIntervalMs]);

  return stats;
}
