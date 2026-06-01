/**
 * Prediction Market Intelligence Page
 * ====================================
 * Deep intelligence from prediction markets — distinct from Markets overview.
 *
 * Markets page = "what's happening now" (quick, at-a-glance)
 * Intelligence page = "what does it mean and what should I do" (analysis, cross-ref)
 *
 * FREE  → Fear Index + breakdown, signal headlines, active market odds, source status
 * BASIC → + Entity cross-reference, deep dive reports, scanner correlation
 * PRO   → + Historical trends, token betting odds lookup, probability swing alerts
 * ELITE → + Custom watchlists, early warning config, export reports
 */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Brain, Target, Shield, AlertTriangle, TrendingUp, TrendingDown,
  Activity, Zap, Lock, Search, BarChart3, Clock, ArrowUpRight,
  Loader2, Radio, Globe, Eye, Crosshair
} from 'lucide-react';
import TierGate from './TierGate';
import { useAppStore } from '../store/appStore';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001';

interface FearIndex {
  overall_risk: number;
  exploit_risk: number;
  regulatory_risk: number;
  stablecoin_risk: number;
  exchange_risk: number;
  generated_at: string;
}

interface IntelSignal {
  signal_type: string;
  severity: string;
  headline: string;
  insight: string;
  action: string;
  confidence: number;
  generated_at: string;
}

interface MarketSource {
  name: string;
  type: string;
  api_count: number;
  endpoints: string[];
  auth: string;
  rate_limits: string;
  url: string;
}

function severityBadge(s: string) {
  const colors: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    high: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    low: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  };
  return `px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${colors[s] || colors.info}`;
}

function fearGauge(value: number, label: string, color: string) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-white/5">
        <div className="h-full rounded-full transition-all duration-700" style={{
          width: `${value}%`,
          backgroundColor: color,
          boxShadow: `0 0 8px ${color}40`,
        }} />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right font-mono">{Math.round(value)}</span>
      <span className="text-[10px] text-gray-500">{label}</span>
    </div>
  );
}

export default function PredictionIntelPage() {
  const user = useAppStore((state) => state.user);
  const tier = user?.tier || 'FREE';

  const [fearIndex, setFearIndex] = useState<FearIndex | null>(null);
  const [signals, setSignals] = useState<IntelSignal[]>([]);
  const [sources, setSources] = useState<MarketSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [tokenQuery, setTokenQuery] = useState('');
  const [tokenResults, setTokenResults] = useState<any[]>([]);
  const [tokenLoading, setTokenLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/intelligence/crypto-fear-index`).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/intelligence/prediction-signals?limit=8`).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/prediction-markets/sources`).then(r => r.json()),
    ]).then(([fear, sigs, srcs]) => {
      if (fear?.overall_risk !== undefined) setFearIndex(fear);
      if (Array.isArray(sigs)) setSignals(sigs);
      if (srcs?.sources) setSources(srcs.sources);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  const searchTokenOdds = async () => {
    if (!tokenQuery.trim()) return;
    setTokenLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/prediction-markets/token/${encodeURIComponent(tokenQuery.trim())}`);
      const d = await r.json();
      setTokenResults(d.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setTokenLoading(false);
    }
  };

  const riskLabel = (v: number) =>
    v >= 75 ? 'EXTREME FEAR' : v >= 50 ? 'FEAR' : v >= 25 ? 'NEUTRAL' : v >= 10 ? 'GREED' : 'EXTREME GREED';

  const riskColor = (v: number) =>
    v >= 75 ? '#FF3366' : v >= 50 ? '#F4A259' : v >= 25 ? '#D1A340' : v >= 10 ? '#00E676' : '#28CBF4';

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a12] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Loading intelligence data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a12] pt-20 px-4 sm:px-6 lg:px-8 pb-20">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <Brain className="w-4 h-4 text-purple-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">Prediction Market Intelligence</h1>
          </div>
          <p className="text-gray-400 text-sm max-w-2xl">
            Deep analysis from live prediction markets — Polymarket, Kalshi, Limitless, Manifold.
            Cross-reference market sentiment with on-chain data to spot threats before they happen.
          </p>
        </motion.div>

        {/* ─── FREE TIER ─────────────────────────────────────── */}
        <div className="space-y-6">
          {/* Row 1: Fear Index + Signal Feed */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Fear Index — Full Breakdown */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
              className="lg:col-span-1 p-6 rounded-2xl bg-[#12121a]/80 backdrop-blur-xl border border-purple-500/10">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Crypto Fear Index</h3>
                <span className="text-[10px] text-gray-500 ml-auto">
                  {riskLabel(fearIndex?.overall_risk || 0)}
                </span>
              </div>

              {/* Large gauge */}
              <div className="flex justify-center mb-4">
                <div className="relative w-28 h-28">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="56" cy="56" r="48" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="8" />
                    <circle cx="56" cy="56" r="48" fill="none" stroke={riskColor(fearIndex?.overall_risk || 0)} strokeWidth="8"
                      strokeDasharray={`${((fearIndex?.overall_risk || 0) / 100) * 302} 302`} strokeLinecap="round"
                      style={{ filter: `drop-shadow(0 0 8px ${riskColor(fearIndex?.overall_risk || 0)}50)`, transition: 'stroke-dasharray 1s ease' }} />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-black" style={{ color: riskColor(fearIndex?.overall_risk || 0) }}>
                      {Math.round(fearIndex?.overall_risk || 0)}
                    </span>
                    <span className="text-[10px] text-gray-500">/100</span>
                  </div>
                </div>
              </div>

              {/* Category breakdowns */}
              <div className="space-y-2">
                {fearIndex && [
                  { label: 'Exploit Risk', val: fearIndex.exploit_risk, desc: 'Hacks, exploits, vulnerabilities' },
                  { label: 'Regulatory', val: fearIndex.regulatory_risk, desc: 'SEC, CFTC, enforcement actions' },
                  { label: 'Stablecoin', val: fearIndex.stablecoin_risk, desc: 'Depeg, collapse risk' },
                  { label: 'Exchange', val: fearIndex.exchange_risk, desc: 'Insolvency, breach risk' },
                ].map(cat => (
                  <div key={cat.label} className="group">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-[10px] text-gray-500">{cat.label}</span>
                      <span className="text-[10px] text-gray-400 font-mono">{Math.round(cat.val)}</span>
                    </div>
                    {fearGauge(cat.val, '', cat.val >= 75 ? '#FF3366' : cat.val >= 50 ? '#F4A259' : cat.val >= 25 ? '#D1A340' : '#00E676')}
                    <div className="text-[9px] text-gray-600 mt-0.5 group-hover:text-gray-500 transition-colors">{cat.desc}</div>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t border-white/5">
                <div className="text-[10px] text-gray-600">
                  Derived from live Polymarket, Kalshi, Manifold, Limitless data.
                  Updated every 5 minutes.
                </div>
              </div>
            </motion.div>

            {/* Signal Feed */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              className="lg:col-span-2 p-6 rounded-2xl bg-[#12121a]/80 backdrop-blur-xl border border-purple-500/10">
              <div className="flex items-center gap-2 mb-4">
                <Radio className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-bold text-white">Live Signal Feed</h3>
                <span className="relative flex h-2 w-2 ml-1">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
              </div>

              {signals.length === 0 ? (
                <div className="text-gray-600 text-xs py-8 text-center">
                  No active signals. Markets are quiet right now.
                </div>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                  {signals.map((s, i) => (
                    <div key={i} className="p-3 rounded-lg bg-black/30 border border-purple-500/5 hover:border-purple-500/20 transition-all">
                      <div className="flex items-start gap-3">
                        <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${s.severity === 'critical' ? 'bg-red-400 animate-pulse' : s.severity === 'high' ? 'bg-amber-400' : 'bg-yellow-400'}`} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={severityBadge(s.severity)}>{s.severity}</span>
                            <span className="text-[10px] text-gray-500">
                              conf: {(s.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="text-sm font-semibold text-white leading-snug">{s.headline}</p>
                          <p className="text-xs text-gray-400 mt-1 leading-relaxed">{s.insight}</p>
                          <div className="mt-2 flex items-center gap-1 text-[10px] text-purple-400/70">
                            <Shield className="w-3 h-3" />
                            <span>{s.action}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          {/* Row 2: Active Markets + Sources */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* PREMIUM: Scanner Cross-Reference */}
            <TierGate
              requiredTier="BASIC"
              title="Scanner Cross-Reference"
              description="Correlate prediction market odds with on-chain scanner results for confirmed threat detection."
            >
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
                className="p-6 rounded-2xl bg-[#12121a]/80 backdrop-blur-xl border border-purple-500/10 h-full">
                <div className="flex items-center gap-2 mb-4">
                  <Crosshair className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-bold text-white">Scanner Cross-Reference</h3>
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 ml-auto">BASIC+</span>
                </div>
                <p className="text-xs text-gray-400 mb-4">
                  Markets say one thing, scanners say another. When prediction markets price in risk
                  that on-chain scanners confirm, the signal is real. This cross-reference finds
                  the overlap.
                </p>
                <div className="p-6 rounded-lg bg-amber-500/5 border border-amber-500/10 text-center">
                  <Eye className="w-6 h-6 text-amber-400/50 mx-auto mb-2" />
                  <p className="text-xs text-amber-400/70">
                    Enter a token address to cross-reference prediction market odds
                    with our SENTINEL scanner results.
                  </p>
                  <p className="text-[10px] text-gray-600 mt-1">
                    Available for BASIC tier and above.
                  </p>
                </div>
              </motion.div>
            </TierGate>

            {/* PREMIUM: Entity Intelligence */}
            <TierGate
              requiredTier="BASIC"
              title="Entity Intelligence"
              description="What are prediction markets saying about specific protocols, exchanges, and entities?"
            >
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                className="p-6 rounded-2xl bg-[#12121a]/80 backdrop-blur-xl border border-purple-500/10 h-full">
                <div className="flex items-center gap-2 mb-4">
                  <Globe className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-bold text-white">Entity Intelligence</h3>
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 ml-auto">BASIC+</span>
                </div>
                <p className="text-xs text-gray-400 mb-4">
                  Track what prediction markets are pricing for specific exchanges, protocols,
                  and crypto entities. Early warning when market probability spikes.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {['Binance', 'Coinbase', 'Tether', 'Ethereum', 'Solana', 'Uniswap'].map(entity => (
                    <div key={entity} className="p-3 rounded-lg bg-black/30 border border-purple-500/5 text-center">
                      <div className="text-xs font-semibold text-white">{entity}</div>
                      <div className="text-[10px] text-gray-500 mt-0.5">No active markets</div>
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-gray-600 mt-3">
                  Entity markets update when prediction markets create new contracts for these entities.
                </p>
              </motion.div>
            </TierGate>
          </div>

          {/* PRO+: Token Betting Odds Search */}
          <TierGate
            requiredTier="PRO"
            title="Token Betting Odds Lookup"
            description="Search prediction markets for what they're pricing about specific tokens."
          >
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
              className="p-6 rounded-2xl bg-[#12121a]/80 backdrop-blur-xl border border-purple-500/10">
              <div className="flex items-center gap-2 mb-4">
                <Search className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-bold text-white">Token Betting Odds</h3>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 ml-auto">PRO+</span>
              </div>
              <p className="text-xs text-gray-400 mb-4">
                What do prediction markets say about a specific token? Search across
                Polymarket, Kalshi, Manifold, and Limitless for markets mentioning any token.
              </p>
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={tokenQuery}
                  onChange={e => setTokenQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && searchTokenOdds()}
                  placeholder="BTC, ETH, SOL, or any token symbol..."
                  className="flex-1 px-3 py-2 bg-black/30 border border-purple-500/20 rounded-lg text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-purple-500/50"
                />
                <button
                  onClick={searchTokenOdds}
                  disabled={tokenLoading}
                  className="px-4 py-2 bg-purple-600/20 border border-purple-500/30 rounded-lg text-purple-400 text-sm font-medium hover:bg-purple-600/30 transition-colors disabled:opacity-50"
                >
                  {tokenLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
                </button>
              </div>
              {tokenResults.length > 0 && (
                <div className="space-y-2">
                  {tokenResults.slice(0, 8).map((m: any, i: number) => (
                    <div key={i} className="p-3 rounded-lg bg-black/30 border border-purple-500/5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-400 font-mono">[{m.source}]</span>
                        <span className={`text-xs font-bold ${m.probability?.yes_pct ? 'text-emerald-400' : 'text-gray-500'}`}>
                          {m.probability?.yes_pct || '?'}
                        </span>
                      </div>
                      <p className="text-sm text-white mt-1">{m.question}</p>
                      {m.volume_usd > 0 && (
                        <p className="text-[10px] text-gray-500 mt-1">
                          Vol: ${m.volume_usd?.toLocaleString()}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </TierGate>

          {/* Data Sources — Free */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="p-6 rounded-2xl bg-[#12121a]/80 backdrop-blur-xl border border-purple-500/10">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-bold text-white">Data Sources</h3>
              <span className="text-[10px] text-gray-500 ml-2">All free, zero authentication for read-only data</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {sources.map(src => (
                <div key={src.name} className="p-3 rounded-lg bg-black/30 border border-purple-500/5">
                  <div className="text-xs font-semibold text-white mb-1">{src.name}</div>
                  <div className="text-[10px] text-gray-400 mb-1">{src.type}</div>
                  <div className="flex items-center gap-1 text-[9px] text-gray-600">
                    <span>{src.api_count} API{src.api_count > 1 ? 's' : ''}</span>
                    <span className="text-gray-700">·</span>
                    <span>{src.auth}</span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
