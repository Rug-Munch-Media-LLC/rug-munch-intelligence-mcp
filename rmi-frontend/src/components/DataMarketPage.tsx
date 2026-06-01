import { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import {
  Search, TrendingUp, TrendingDown, ArrowUp, ArrowDown,
  Loader2, RefreshCw, Shield, Globe, ChevronRight, Activity
} from 'lucide-react';
import { motion } from 'framer-motion';

const CHAINS = [
  { id: 'all', name: 'All Chains', icon: 'A' },
  { id: 'solana', name: 'Solana', icon: 'S', color: '#9945FF' },
  { id: 'base', name: 'Base', icon: 'B', color: '#0052FF' },
  { id: 'ethereum', name: 'Ethereum', icon: 'E', color: '#627EEA' },
  { id: 'bsc', name: 'BSC', icon: 'BNB', color: '#F0B90B' },
];

const SORT_TABS = [
  { id: 'trending', label: 'Trending', icon: TrendingUp },
  { id: 'gainers', label: 'Gainers', icon: ArrowUp },
  { id: 'losers', label: 'Losers', icon: ArrowDown },
];

const API_BASE = '';

export default function DataMarketPage() {
  const setCurrentPage = useAppStore((s) => s.setCurrentPage);

  const [activeChain, setActiveChain] = useState('all');
  const [activeSort, setActiveSort] = useState('trending');
  const [tokens, setTokens] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const chainParam = activeChain === 'all' ? 'sol' : activeChain;
      const res = await fetch(`${API_BASE}/api/v1/rugmaps/trending?chain=${chainParam}&limit=50`);
      const data = await res.json();
      let list = data.trending || data.tokens || data.data || [];
      if (!Array.isArray(list)) list = [];

      // Fallback to DexScreener if empty
      if (list.length === 0) {
        try {
          const dexRes = await fetch('https://api.dexscreener.com/latest/dex/tokens/trending');
          const dexData = await dexRes.json();
          const pairs = dexData.pairs || [];
          list = pairs.slice(0, 50).map((p: any) => ({
            address: p.baseToken?.address || p.pairAddress,
            name: p.baseToken?.name || 'Unknown',
            symbol: p.baseToken?.symbol || '???',
            price_usd: parseFloat(p.priceUsd) || 0,
            volume_24h: (p.volume?.h24 || 0),
            price_change_24h: (p.priceChange?.h24 || 0),
            liquidity: (p.liquidity?.usd || 0),
            chain: p.chainId,
            risk_score: null,
            risk_level: 'UNKNOWN',
            red_flags: [],
          }));
        } catch { /* ignore */ }
      }

      setTokens(list);
      setLastUpdated(new Date());
    } catch {
      setTokens([]);
    } finally {
      setLoading(false);
    }
  }, [activeChain]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const filtered = tokens.filter((t) => {
    const q = searchQuery.toLowerCase();
    if (!q) return true;
    return (
      (t.name || '').toLowerCase().includes(q) ||
      (t.symbol || '').toLowerCase().includes(q) ||
      (t.address || '').toLowerCase().includes(q)
    );
  });

  const sorted = [...filtered].sort((a, b) => {
    if (activeSort === 'gainers') return (b.price_change_24h || 0) - (a.price_change_24h || 0);
    if (activeSort === 'losers') return (a.price_change_24h || 0) - (b.price_change_24h || 0);
    // trending: risk score desc (highest risk first), then volume
    return (b.risk_score ?? b.volume_24h ?? 0) - (a.risk_score ?? a.volume_24h ?? 0);
  });

  const riskColor = (level?: string) => {
    const l = (level || '').toLowerCase();
    if (l.includes('critical')) return 'bg-red-600 text-white';
    if (l.includes('high')) return 'bg-orange-500 text-white';
    if (l.includes('medium')) return 'bg-yellow-500 text-black';
    if (l.includes('low') || l.includes('safe')) return 'bg-emerald-500 text-white';
    return 'bg-white/10 text-white/60';
  };

  const riskScoreColor = (score?: number) => {
    if (score == null) return '#6b7280';
    if (score >= 80) return '#ef4444';
    if (score >= 60) return '#f97316';
    if (score >= 40) return '#eab308';
    if (score >= 20) return '#84cc16';
    return '#22c55e';
  };

  const highRisk = sorted.filter((t) => {
    const s = t.risk_score ?? 50;
    return s >= 60;
  }).length;
  const safe = sorted.filter((t) => {
    const s = t.risk_score ?? 50;
    return s < 20;
  }).length;

  const fmtUsd = (val: number) => {
    if (!val) return '—';
    if (val >= 1e9) return '$' + (val / 1e9).toFixed(2) + 'B';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(2) + 'M';
    if (val >= 1e3) return '$' + (val / 1e3).toFixed(1) + 'K';
    return '$' + val.toLocaleString(undefined, { maximumFractionDigits: 8 });
  };

  return (
    <div className="min-h-screen bg-[#07070b] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#0e0e16]/80 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-[1400px] mx-auto px-6 py-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#8B5CF6] to-[#D1A340] flex items-center justify-center font-bold text-lg">
                DM
              </div>
              <div>
                <h1 className="font-bold text-lg tracking-tight">Data Market</h1>
                <p className="text-xs text-white/40">Live Intelligence-Overlay Market Data</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3 text-xs">
                <span className="px-2.5 py-1 bg-red-500/20 text-red-400 rounded-full font-bold">{highRisk} HIGH RISK</span>
                <span className="px-2.5 py-1 bg-emerald-500/20 text-emerald-400 rounded-full font-bold">{safe} SAFE</span>
                <span className="text-white/30">{sorted.length} total</span>
              </div>
              <button
                onClick={fetchData}
                disabled={loading}
                className="px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm flex items-center gap-2 transition-colors disabled:opacity-40"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Refresh'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-6 py-6 space-y-4">
        {/* Chain + Sort controls */}
        <div className="flex flex-col sm:flex-row gap-3 justify-between">
          <div className="flex gap-1 bg-white/5 rounded-lg p-1 overflow-x-auto">
            {CHAINS.map((c) => (
              <button
                key={c.id}
                onClick={() => setActiveChain(c.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap ${
                  activeChain === c.id ? 'bg-[#8B5CF6] text-white' : 'text-white/50 hover:text-white hover:bg-white/5'
                }`}
              >
                {c.icon} {c.name}
              </button>
            ))}
          </div>

          <div className="flex gap-1 bg-white/5 rounded-lg p-1">
            {SORT_TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveSort(t.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeSort === t.id ? 'bg-white/15 text-white' : 'text-white/50 hover:text-white hover:bg-white/5'
                }`}
              >
                <t.icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tokens by name, symbol, or address..."
            className="w-full bg-[#0e0e16] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-[#8B5CF6] placeholder:text-white/20"
          />
        </div>

        {/* Token Table */}
        <div className="bg-[#0e0e16] border border-white/10 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-white/40 border-b border-white/10 text-xs">
                  <th className="text-left py-3 px-4 w-10">#</th>
                  <th className="text-left py-3 px-4">Token</th>
                  <th className="text-right py-3 px-4">Price</th>
                  <th className="text-right py-3 px-4">24h %</th>
                  <th className="text-right py-3 px-4">Volume 24h</th>
                  <th className="text-right py-3 px-4">Liquidity</th>
                  <th className="text-center py-3 px-4">Risk</th>
                  <th className="text-right py-3 px-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-[#8B5CF6] mx-auto" />
                    </td>
                  </tr>
                ) : sorted.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-white/30">
                      <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      No tokens found
                    </td>
                  </tr>
                ) : (
                  sorted.map((token, i) => (
                    <motion.tr
                      key={token.address || i}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: Math.min(i * 0.03, 0.5) }}
                      onClick={() => {
                        if (token.address) {
                          setCurrentPage('rugcharts');
                        }
                      }}
                      className="border-b border-white/5 hover:bg-white/[0.03] cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 text-white/30 font-mono">{i + 1}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#8B5CF6]/20 to-[#28CBF4]/20 flex items-center justify-center text-[10px] font-bold text-[#8B5CF6]">
                            {(token.symbol || '??').slice(0, 2)}
                          </div>
                          <div>
                            <div className="font-semibold text-sm">{token.name || 'Unknown'}</div>
                            <div className="text-[10px] text-white/30 font-mono">{token.symbol || '???'}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-mono">{fmtUsd(token.price_usd)}</td>
                      <td className={`py-3 px-4 text-right font-mono font-medium ${(token.price_change_24h || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {(token.price_change_24h || 0) >= 0 ? '+' : ''}{(token.price_change_24h || 0).toFixed(2)}%
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-white/50">{fmtUsd(token.volume_24h)}</td>
                      <td className="py-3 px-4 text-right font-mono text-white/50">{fmtUsd(token.liquidity)}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${riskColor(token.risk_level)}`}>
                          {token.risk_level || (token.risk_score != null ? (token.risk_score >= 60 ? 'HIGH' : token.risk_score >= 40 ? 'MED' : token.risk_score >= 20 ? 'LOW' : 'SAFE') : '?')}
                        </span>
                        {token.risk_score != null && (
                          <div className="text-[10px] mt-0.5 font-mono" style={{ color: riskScoreColor(token.risk_score) }}>
                            {token.risk_score}/100
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <ChevronRight className="w-4 h-4 text-white/20" />
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer note */}
        <div className="text-center text-xs text-white/20 py-2">
          Click any token to run full forensic analysis · Data refreshes every 30s · Intelligence overlay from RugMunch AI
        </div>

        {/* Feature cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-4">
          {[
            { icon: Shield, title: 'Risk Scoring', desc: 'AI-powered risk assessment on every token', color: '#8B5CF6' },
            { icon: Globe, title: 'Multi-Chain', desc: 'Solana, Base, Ethereum, BSC coverage', color: '#28CBF4' },
            { icon: Activity, title: 'Real-Time', desc: 'Live price, volume, and liquidity data', color: '#00E676' },
            { icon: TrendingUp, title: 'Forensic Deep-Dive', desc: 'One-click full security audit', color: '#D1A340' },
          ].map((card, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.1 }}
              className="bg-[#0e0e16] border border-white/10 rounded-xl p-4"
            >
              <card.icon className="w-5 h-5 mb-2" style={{ color: card.color }} />
              <h4 className="font-semibold text-sm mb-1">{card.title}</h4>
              <p className="text-xs text-white/40">{card.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
