/**
 * HeroSection — Main landing hero with real-time alert feed
 * Alerts poll from /api/v1/alerts/recent every 5s (with fallback to SSE)
 */
import { useState, useEffect, useRef } from 'react';
import {
  Check, AlertTriangle, Activity, Radio, Sparkles, ChevronRight,
  Search, Shield, Gift, Heart, MessageCircle, Share2, ArrowRight,
  Flame, Skull, Zap
} from 'lucide-react';
import NeuralNetwork from '../hero/NeuralNetwork';
import HeroText from '../hero/HeroText';
import ScrollReveal from '../hero/ScrollReveal';
import api from '../../services/api';

interface LiveAlert {
  id?: string;
  severity: string;
  title: string;
  description: string;
  chain: string;
  time: string;
  contract?: string;
  likes?: number;
  comments?: number;
  shares?: number;
  verified?: boolean;
  source?: string;
  alert_type?: string;
  message?: string;
  token_symbol?: string;
  wallet_address?: string;
  timestamp?: string;
}

function getSeverityColor(severity: string) {
  switch (severity?.toLowerCase()) {
    case 'critical': return 'text-red-400 bg-red-500/10 border-red-500/30';
    case 'high':
    case 'warning': return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
    case 'medium':
    case 'info': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    default: return 'text-gray-400 bg-gray-500/10 border-gray-500/30';
  }
}

function getSeverityIcon(severity: string) {
  switch (severity?.toLowerCase()) {
    case 'critical': return <Skull className="w-4 h-4 text-red-400" />;
    case 'high':
    case 'warning': return <AlertTriangle className="w-4 h-4 text-orange-400" />;
    case 'medium':
    case 'info': return <Activity className="w-4 h-4 text-yellow-400" />;
    default: return <Radio className="w-4 h-4 text-gray-400" />;
  }
}

function formatTime(ts: string): string {
  if (!ts) return '';
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/** Normalize raw alert from /api/v1/alerts/recent into LiveAlert shape */
function normalizeAlert(raw: any): LiveAlert {
  return {
    id: raw.id ?? raw.timestamp,
    severity: (raw.level ?? raw.severity ?? 'info').toLowerCase(),
    title: raw.title ?? raw.alert_type ?? raw.source ?? 'Security Alert',
    description: raw.message ?? raw.description ?? '',
    chain: raw.chain ?? raw.metadata?.chain ?? 'SOL',
    time: formatTime(raw.timestamp ?? raw.created_at ?? raw.scanned_at ?? ''),
    contract: raw.address ?? raw.token ?? raw.contract,
    source: raw.source ?? raw.event,
    token_symbol: raw.token_symbol ?? raw.symbol,
    verified: true,
  };
}

// Fallback alerts in case backend is unreachable (so hero never shows empty)
const FALLBACK_ALERTS: LiveAlert[] = [
  { severity: 'info', title: 'Connecting to live feed...', description: 'Real-time scam alerts will appear here. Scanners are actively monitoring 8 chains.', chain: 'ALL', time: 'loading', verified: true },
];

interface HeroSectionProps {
  onNavigate: (page: string) => void;
  onAirdropClick: () => void;
}

export default function HeroSection({ onNavigate, onAirdropClick }: HeroSectionProps) {
  const [alerts, setAlerts] = useState<LiveAlert[]>(FALLBACK_ALERTS);
  const [liveConnected, setLiveConnected] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await api.client.get('/api/v1/alerts/recent', { params: { limit: 8 } });
        const data = res.data?.alerts ?? res.data ?? [];
        if (Array.isArray(data) && data.length > 0) {
          setAlerts(data.map(normalizeAlert));
          setLiveConnected(true);
        }
      } catch {
        // Keep fallback alerts — backend might be mid-scan
      }
    };

    fetchAlerts();
    pollRef.current = setInterval(fetchAlerts, 8000);
    return () => clearInterval(pollRef.current);
  }, []);

  return (
    <section className="relative pt-36 pb-16 px-4 sm:px-6 lg:px-8 overflow-hidden min-h-[90vh] flex flex-col">
      <NeuralNetwork />

      <div className="relative z-10 max-w-7xl mx-auto w-full">
        <div className="grid lg:grid-cols-5 gap-8">
          {/* Main Hero Content - 3 columns */}
          <div className="lg:col-span-3 text-center lg:text-left">
            <ScrollReveal direction="down" delay={0} distance={20}>
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/10 border border-purple-500/30 rounded-full mb-6 backdrop-blur-sm">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span className="text-purple-400 text-sm font-medium">V2 Live — 8 Chains Monitored</span>
                <ChevronRight className="w-4 h-4 text-purple-400" />
              </div>
            </ScrollReveal>

            <HeroText />

            <ScrollReveal direction="up" delay={400} distance={30}>
              <div className="bg-[#12121a]/90 backdrop-blur-xl border border-purple-500/20 rounded-xl p-4 mb-8 max-w-lg mx-auto lg:mx-0">
                <div className="flex items-center gap-3 mb-3">
                  <Search className="w-5 h-5 text-purple-400" />
                  <span className="text-sm text-gray-400">Quick Contract Scanner</span>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter token contract address..."
                    className="flex-1 bg-black/50 border border-purple-500/20 rounded-lg px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                    onClick={() => onNavigate('token-scan')}
                    readOnly
                  />
                  <button
                    onClick={() => onNavigate('token-scan')}
                    className="px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600 text-white font-semibold rounded-lg transition-all"
                  >
                    Scan
                  </button>
                </div>
              </div>
            </ScrollReveal>

            <ScrollReveal direction="up" delay={600} distance={30}>
              <div className="flex flex-col sm:flex-row items-center lg:items-start gap-4 mb-8">
                <button
                  onClick={() => onNavigate('token-scan')}
                  className="w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-purple-600 to-yellow-500 hover:from-purple-500 hover:to-yellow-400 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-all transform hover:scale-105 shadow-lg shadow-purple-500/20"
                >
                  <Shield className="w-5 h-5" />
                  CHECK SCAMS NOW
                </button>
                <button
                  onClick={onAirdropClick}
                  className="w-full sm:w-auto px-8 py-4 bg-[#12121a]/80 backdrop-blur border border-yellow-500/30 hover:border-yellow-500/50 text-yellow-400 font-semibold rounded-xl flex items-center justify-center gap-2 transition-all"
                >
                  <Gift className="w-5 h-5" />
                  Join Airdrop Waitlist
                </button>
              </div>
            </ScrollReveal>

            <ScrollReveal direction="up" delay={800} distance={20}>
              <div className="flex flex-wrap items-center justify-center lg:justify-start gap-6 text-sm text-gray-500">
                <span className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-purple-400" />
                  AI-Powered Analysis
                </span>
                <span className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-purple-400" />
                  28+ Data Sources
                </span>
                <span className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-purple-400" />
                  8 Chains Monitored
                </span>
              </div>
            </ScrollReveal>
          </div>

          {/* Live Alert Feed Sidebar - 2 columns */}
          <div className="lg:col-span-2">
            <ScrollReveal direction="left" delay={300} distance={50}>
              <div className="bg-[#0a0a12]/90 backdrop-blur-xl border border-purple-500/20 rounded-xl overflow-hidden shadow-2xl shadow-purple-950/30">
                <div className="p-4 border-b border-purple-500/20 bg-gradient-to-r from-purple-950/40 to-transparent">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Radio className={`w-5 h-5 ${liveConnected ? 'text-red-400 animate-pulse' : 'text-slate-600'}`} />
                      <span className="font-semibold text-white">Live Threat Feed</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${liveConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                      <span className={`text-xs ${liveConnected ? 'text-emerald-400' : 'text-slate-600'}`}>
                        {liveConnected ? 'LIVE' : 'CONNECTING'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="max-h-[480px] overflow-y-auto scrollbar-thin scrollbar-thumb-purple-900/30">
                  {alerts.map((alert, i) => (
                    <div
                      key={alert.id ?? i}
                      className="p-4 border-b border-purple-500/10 hover:bg-purple-500/5 transition-colors cursor-pointer"
                      onClick={() => onNavigate('threat-feed')}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`p-1.5 rounded-lg ${getSeverityColor(alert.severity)}`}>
                          {getSeverityIcon(alert.severity)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${getSeverityColor(alert.severity)}`}>
                              {alert.severity}
                            </span>
                            <span className="text-[10px] text-slate-600">{alert.time}</span>
                            <span className="text-[10px] text-purple-400 font-mono">{alert.chain}</span>
                          </div>
                          <h4 className="font-semibold text-sm mb-1 truncate text-white/90">{alert.title}</h4>
                          <p className="text-xs text-slate-500 line-clamp-2">{alert.description}</p>
                          {alert.contract && (
                            <p className="text-[10px] text-slate-600 font-mono mt-1 truncate">{alert.contract}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  {alerts.length === 0 && (
                    <div className="p-8 text-center">
                      <Radio className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                      <p className="text-slate-600 text-sm">No active threats detected</p>
                      <p className="text-slate-700 text-xs mt-1">All clear across monitored chains</p>
                    </div>
                  )}
                </div>

                <div className="p-3 border-t border-purple-500/20 bg-gradient-to-r from-transparent to-purple-950/20">
                  <button
                    onClick={() => onNavigate('threat-feed')}
                    className="w-full py-2 text-sm text-purple-400 hover:text-purple-300 transition-colors flex items-center justify-center gap-2 font-medium"
                  >
                    View All Alerts
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </ScrollReveal>
          </div>
        </div>
      </div>
    </section>
  );
}
