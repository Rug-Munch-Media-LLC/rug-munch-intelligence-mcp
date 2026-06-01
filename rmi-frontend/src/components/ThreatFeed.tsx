/**
 * ThreatFeed — Real-Time Scam Alert Stream
 * WebSocket at /ws/v1/stream/alerts with HTTP fallback polling
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  AlertTriangle, Shield, Info, Bell, BellOff, Pause, Play,
  Download, ChevronDown, ChevronUp, Filter, Radio, Wifi, WifiOff,
  Zap, Volume2, VolumeX
} from 'lucide-react';
import api from '../services/api';

// ─── Types ────────────────────────────────────────────────

type AlertLevel = 'CRITICAL' | 'WARNING' | 'INFO';

interface Alert {
  id: string;
  level: AlertLevel;
  source: string;
  token?: string;
  wallet?: string;
  message: string;
  timestamp: string;
  details?: Record<string, any>;
}

const SEVERITY_CONFIG: Record<AlertLevel, { color: string; bg: string; border: string; pulse: string; icon: any }> = {
  CRITICAL: {
    color: 'text-red-400',
    bg: 'bg-red-950/30',
    border: 'border-red-800/40',
    pulse: 'animate-pulse bg-red-500',
    icon: AlertTriangle,
  },
  WARNING: {
    color: 'text-yellow-400',
    bg: 'bg-yellow-950/20',
    border: 'border-yellow-800/40',
    pulse: 'bg-yellow-500',
    icon: Shield,
  },
  INFO: {
    color: 'text-blue-400',
    bg: 'bg-blue-950/20',
    border: 'border-blue-800/40',
    pulse: 'bg-blue-500',
    icon: Info,
  },
};

const MAX_ALERTS = 200;

export default function ThreatFeed() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [paused, setPaused] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<AlertLevel | 'ALL'>('ALL');
  const [wsConnected, setWsConnected] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number>(0);
  const soundRef = useRef<AudioContext | null>(null);

  // ─── Severity Counts ────────────────────────────────────

  const counts = alerts.reduce(
    (acc, a) => {
      acc[a.level] = (acc[a.level] || 0) + 1;
      return acc;
    },
    { CRITICAL: 0, WARNING: 0, INFO: 0 } as Record<AlertLevel, number>
  );

  // ─── Sound Beep ──────────────────────────────────────────

  const playBeep = useCallback(() => {
    if (!soundEnabled) return;
    try {
      const ctx = soundRef.current || new AudioContext();
      soundRef.current = ctx;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = 'square';
      gain.gain.value = 0.15;
      osc.start();
      osc.stop(ctx.currentTime + 0.15);
    } catch {
      // Audio context may not be available
    }
  }, [soundEnabled]);

  // ─── Add Alert ───────────────────────────────────────────

  const addAlert = useCallback(
    (alert: Alert) => {
      setAlerts((prev) => {
        const next = [alert, ...prev].slice(0, MAX_ALERTS);
        return next;
      });
      if (alert.level === 'CRITICAL') playBeep();
    },
    [playBeep]
  );

  // ─── WebSocket ───────────────────────────────────────────

  const connectWs = useCallback(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/v1/stream/alerts`;
    const token = localStorage.getItem('access_token');
    const fullUrl = token ? `${wsUrl}?token=${token}` : wsUrl;

    try {
      const ws = new WebSocket(fullUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        reconnectRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const alert: Alert = {
            id: data.id || crypto.randomUUID(),
            level: data.level || data.severity || 'INFO',
            source: data.source || 'unknown',
            token: data.token || data.token_address,
            wallet: data.wallet || data.wallet_address,
            message: data.message || data.text || '',
            timestamp: data.timestamp || new Date().toISOString(),
            details: data.details || data.data,
          };
          addAlert(alert);
        } catch {
          // ignore malformed
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        const delay = Math.min(5000 * (reconnectRef.current + 1), 30000);
        reconnectRef.current += 1;
        setTimeout(connectWs, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setWsConnected(false);
    }
  }, [addAlert]);

  useEffect(() => {
    connectWs();
    return () => {
      wsRef.current?.close();
    };
  }, [connectWs]);

  // ─── HTTP Fallback Polling ───────────────────────────────

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await api.client.get('/api/v1/alerts/recent');
        const recent: Alert[] = (data.data?.alerts || data.data || []).map((a: any) => ({
          id: a.id || crypto.randomUUID(),
          level: a.level || a.severity || 'INFO',
          source: a.source || 'unknown',
          token: a.token || a.token_address,
          wallet: a.wallet || a.wallet_address,
          message: a.message || a.text || '',
          timestamp: a.timestamp || a.created_at || new Date().toISOString(),
          details: a.details || a.data,
        }));
        setAlerts((prev) => {
          const existingIds = new Set(prev.map((p) => p.id));
          const newOnes = recent.filter((r) => !existingIds.has(r.id));
          if (newOnes.length === 0) return prev;
          return [...newOnes, ...prev].slice(0, MAX_ALERTS);
        });
      } catch {
        // polling fallback fail silently
      }
    };
    poll();
    const interval = setInterval(poll, 30000);
    return () => clearInterval(interval);
  }, []);

  // ─── Auto-scroll ─────────────────────────────────────────

  useEffect(() => {
    if (!paused && feedRef.current) {
      feedRef.current.scrollTop = 0;
    }
  }, [alerts, paused]);

  // ─── Export ──────────────────────────────────────────────

  const exportAlerts = () => {
    const json = JSON.stringify(alerts, null, 2);
    navigator.clipboard.writeText(json);
  };

  // ─── Filtered alerts ─────────────────────────────────────

  const filtered = filterSeverity === 'ALL' ? alerts : alerts.filter((a) => a.level === filterSeverity);

  // ─── Render ──────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-slate-200 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-purple-950/60 border border-purple-800/40 flex items-center justify-center">
              <Radio className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Threat Feed</h1>
              <p className="text-xs text-purple-400/70 font-mono tracking-wider uppercase">Real-time scam alerts</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Live indicator */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/60 border border-slate-700/40 text-xs">
              <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
              <span className={wsConnected ? 'text-emerald-400' : 'text-red-400'}>
                {wsConnected ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>

        {/* Severity counters */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {(['CRITICAL', 'WARNING', 'INFO'] as AlertLevel[]).map((level) => {
            const cfg = SEVERITY_CONFIG[level];
            const Icon = cfg.icon;
            return (
              <button
                key={level}
                onClick={() => setFilterSeverity(filterSeverity === level ? 'ALL' : level)}
                className={`flex items-center gap-2 p-3 rounded-xl border transition-colors ${
                  filterSeverity === level
                    ? `${cfg.bg} ${cfg.border}`
                    : 'bg-slate-900/40 border-slate-800/40 hover:bg-slate-800/40'
                }`}
              >
                <span className={`w-3 h-3 rounded-full ${cfg.pulse}`} style={level === 'CRITICAL' ? { animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' } : undefined} />
                <Icon className={`w-4 h-4 ${cfg.color}`} />
                <div className="text-left">
                  <div className={`text-lg font-bold ${cfg.color}`}>{counts[level]}</div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider">{level}</div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setPaused(!paused)}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1.5 transition-colors border border-slate-700/50"
          >
            {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`px-3 py-1.5 text-xs rounded-lg flex items-center gap-1.5 transition-colors border ${
              soundEnabled
                ? 'bg-red-950/30 border-red-800/40 text-red-400'
                : 'bg-slate-800 hover:bg-slate-700 border-slate-700/50 text-slate-300'
            }`}
          >
            {soundEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
            {soundEnabled ? 'Sound On' : 'Sound Off'}
          </button>
          {filterSeverity !== 'ALL' && (
            <button
              onClick={() => setFilterSeverity('ALL')}
              className="px-3 py-1.5 text-xs rounded-lg bg-purple-950/40 border border-purple-800/40 text-purple-300 flex items-center gap-1.5 transition-colors"
            >
              <Filter className="w-3.5 h-3.5" />
              Clear Filter
            </button>
          )}
          <div className="flex-1" />
          <button
            onClick={exportAlerts}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1.5 transition-colors border border-slate-700/50"
          >
            <Download className="w-3.5 h-3.5" />
            Export JSON
          </button>
        </div>

        {/* Alert feed */}
        <div
          ref={feedRef}
          className="space-y-2 max-h-[calc(100vh-380px)] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent"
        >
          {filtered.length === 0 && (
            <div className="bg-slate-900/30 border border-slate-800/30 rounded-xl p-8 text-center">
              <Radio className="w-12 h-12 text-purple-500/30 mx-auto mb-3" />
              <p className="text-slate-400 text-sm">Waiting for alerts...</p>
              <p className="text-slate-500 text-xs mt-1">
                {wsConnected ? 'Connected to live stream' : 'Attempting to connect...'}
              </p>
            </div>
          )}
          {filtered.map((alert) => {
            const cfg = SEVERITY_CONFIG[alert.level];
            const Icon = cfg.icon;
            const isExpanded = expandedId === alert.id;
            return (
              <div
                key={alert.id}
                className={`${cfg.bg} border ${cfg.border} rounded-xl cursor-pointer transition-all hover:brightness-110`}
                onClick={() => setExpandedId(isExpanded ? null : alert.id)}
              >
                <div className="flex items-center gap-3 p-3">
                  <span className={`w-3 h-3 rounded-full flex-shrink-0 ${cfg.pulse}`} style={alert.level === 'CRITICAL' ? { animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' } : undefined} />
                  <Icon className={`w-4 h-4 flex-shrink-0 ${cfg.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${cfg.color}`}>{alert.level}</span>
                      <span className="text-[10px] text-slate-500 bg-slate-800/60 px-1.5 py-0.5 rounded">{alert.source}</span>
                      {alert.token && (
                        <span className="text-[10px] text-slate-400 truncate max-w-[120px]">{alert.token.slice(0, 6)}...{alert.token.slice(-4)}</span>
                      )}
                      {alert.wallet && (
                        <span className="text-[10px] text-slate-400 truncate max-w-[120px]">{alert.wallet.slice(0, 6)}...{alert.wallet.slice(-4)}</span>
                      )}
                    </div>
                    <p className="text-sm text-white/80 mt-0.5 truncate">{alert.message}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[10px] text-slate-500">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
                  </div>
                </div>
                {isExpanded && (
                  <div className="px-3 pb-3 border-t border-slate-800/30 pt-2">
                    <div className="text-xs text-slate-400 space-y-1">
                      {alert.token && <div><span className="text-slate-500">Token:</span> {alert.token}</div>}
                      {alert.wallet && <div><span className="text-slate-500">Wallet:</span> {alert.wallet}</div>}
                      <div><span className="text-slate-500">Source:</span> {alert.source}</div>
                      <div><span className="text-slate-500">Time:</span> {new Date(alert.timestamp).toLocaleString()}</div>
                      {alert.details && (
                        <pre className="text-[10px] text-slate-500 bg-slate-950/50 rounded p-2 overflow-x-auto mt-1">
                          {JSON.stringify(alert.details, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}