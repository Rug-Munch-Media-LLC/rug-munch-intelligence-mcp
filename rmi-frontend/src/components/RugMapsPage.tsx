import { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import {
  Search, Shield, AlertTriangle, CheckCircle, XCircle, Loader2,
  ExternalLink, Globe, Database, BarChart3, Users, Zap,
  ChevronRight, RefreshCw, Copy, Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const CHAINS = [
  { id: 'solana', name: 'Solana', icon: 'S', explorer: 'https://solscan.io/token/', color: '#9945FF' },
  { id: 'base', name: 'Base', icon: 'B', explorer: 'https://basescan.org/token/', color: '#0052FF' },
  { id: 'ethereum', name: 'Ethereum', icon: 'E', explorer: 'https://etherscan.io/token/', color: '#627EEA' },
  { id: 'bsc', name: 'BSC', icon: 'BNB', explorer: 'https://bscscan.com/token/', color: '#F0B90B' },
];

const API_BASE = '';

export default function RugMapsPage() {
  const setCurrentPage = useAppStore((s) => s.setCurrentPage);

  const [chain, setChain] = useState('solana');
  const [searchAddr, setSearchAddr] = useState('');
  const [trending, setTrending] = useState<any[]>([]);
  const [trendingLoading, setTrendingLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<any | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [dexData, setDexData] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchTrending = useCallback(async () => {
    setTrendingLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/rugmaps/trending?chain=${chain}&limit=12`);
      const data = await res.json();
      const list = data.trending || data.tokens || data.data || [];
      setTrending(Array.isArray(list) ? list : []);
    } catch {
      setTrending([]);
    } finally {
      setTrendingLoading(false);
    }
  }, [chain]);

  useEffect(() => {
    fetchTrending();
  }, [fetchTrending]);

  const handleScan = async (addr?: string) => {
    const target = (addr || searchAddr).trim();
    if (!target) return;
    setScanning(true);
    setScanError(null);
    setScanResult(null);
    setDexData(null);

    try {
      const [scanRes, dexRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/rugmaps/scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address: target, chain }),
        }),
        fetch(`https://api.dexscreener.com/latest/dex/tokens/${target}`).catch(() => null),
      ]);

      const scanData = await scanRes.json().catch(() => null);
      const dexJson = dexRes ? await dexRes.json().catch(() => null) : null;

      if (scanData?.success && scanData.data) {
        setScanResult(scanData.data);
      } else if (scanData && typeof scanData === 'object') {
        // Flat response
        setScanResult(scanData);
      } else {
        setScanError('Scan returned no data');
      }

      if (dexJson?.pairs?.length) {
        setDexData(dexJson.pairs[0]);
      }
    } catch (e: any) {
      setScanError(e.message || 'Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const copyAddress = (addr: string) => {
    navigator.clipboard.writeText(addr);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const riskColor = (level: string | undefined) => {
    const l = (level || '').toLowerCase();
    if (l.includes('critical')) return 'bg-red-600 text-white';
    if (l.includes('high')) return 'bg-orange-500 text-white';
    if (l.includes('medium')) return 'bg-yellow-500 text-black';
    if (l.includes('low') || l.includes('safe')) return 'bg-emerald-500 text-white';
    return 'bg-gray-500 text-white';
  };

  const riskScoreColor = (score: number) => {
    if (score >= 80) return '#ef4444';
    if (score >= 60) return '#f97316';
    if (score >= 40) return '#eab308';
    if (score >= 20) return '#84cc16';
    return '#22c55e';
  };

  const chainCfg = CHAINS.find((c) => c.id === chain) || CHAINS[0];
  const security = scanResult?.security || {};
  const clusters = scanResult?.clusters || [];
  const findings = scanResult?.findings || {};
  const redFlags = findings.red_flags || [];
  const greenFlags = findings.green_flags || [];
  const bundle = scanResult?.bundle_analysis || {};

  return (
    <div className="min-h-screen bg-[#07070b] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#0e0e16]/80 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#8B5CF6] to-[#28CBF4] flex items-center justify-center font-bold text-lg">
              RM
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight">RugMaps</h1>
              <p className="text-xs text-white/40">Token Map & Wallet Clustering</p>
            </div>
          </div>

          {/* Chain selector */}
          <div className="flex gap-1 bg-white/5 rounded-lg p-1">
            {CHAINS.map((c) => (
              <button
                key={c.id}
                onClick={() => { setChain(c.id); setScanResult(null); setDexData(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  chain === c.id ? 'bg-[#8B5CF6] text-white' : 'text-white/50 hover:text-white hover:bg-white/5'
                }`}
              >
                {c.icon}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-6 py-6 space-y-6">
        {/* Search bar */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex gap-3"
        >
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              value={searchAddr}
              onChange={(e) => setSearchAddr(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleScan()}
              placeholder="Enter token address (e.g., So11111111111111111111111111111111111111112)"
              className="w-full bg-[#0e0e16] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:border-[#8B5CF6] placeholder:text-white/20"
            />
          </div>
          <button
            onClick={() => handleScan()}
            disabled={scanning || !searchAddr.trim()}
            className="px-6 py-3 bg-[#8B5CF6] hover:bg-[#7C4FE0] disabled:opacity-40 rounded-xl font-semibold text-sm flex items-center gap-2 transition-colors"
          >
            {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            Scan
          </button>
          <button
            onClick={fetchTrending}
            className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm flex items-center gap-2 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </motion.div>

        {/* Scan Results */}
        <AnimatePresence>
          {scanResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              {/* Token Header Card */}
              <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold"
                      style={{ background: chainCfg.color + '20', color: chainCfg.color }}
                    >
                      {(scanResult.token?.symbol || '??').slice(0, 2)}
                    </div>
                    <div>
                      <h2 className="text-xl font-bold">{scanResult.token?.name || 'Unknown Token'}</h2>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-sm text-white/50 font-mono">{scanResult.token?.address || searchAddr}</span>
                        <button onClick={() => copyAddress(scanResult.token?.address || searchAddr)} className="text-white/30 hover:text-white/60">
                          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                        <a href={chainCfg.explorer + (scanResult.token?.address || searchAddr)} target="_blank" rel="noopener noreferrer" className="text-[#28CBF4] hover:text-[#5EE0FF]">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${riskColor(scanResult.risk_level)}`}>
                      {scanResult.risk_level || 'UNKNOWN'}
                    </span>
                    <div className="text-sm text-white/40 mt-1">Risk Score: {scanResult.risk_score ?? 'N/A'}</div>
                  </div>
                </div>

                {/* Price Row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5">
                  <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-white/40">Price</div>
                    <div className="font-mono text-lg font-bold">
                      ${scanResult.market?.price_usd?.toLocaleString() || dexData?.priceUsd || 'N/A'}
                    </div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-white/40">Market Cap</div>
                    <div className="font-mono text-lg font-bold">
                      ${scanResult.market?.market_cap ? (scanResult.market.market_cap / 1e6).toFixed(2) + 'M' : 'N/A'}
                    </div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-white/40">Volume 24h</div>
                    <div className="font-mono text-lg font-bold">
                      ${scanResult.market?.volume_24h ? (scanResult.market.volume_24h / 1e6).toFixed(2) + 'M' : 'N/A'}
                    </div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-3">
                    <div className="text-xs text-white/40">Liquidity</div>
                    <div className="font-mono text-lg font-bold">
                      ${scanResult.market?.liquidity_usd ? (scanResult.market.liquidity_usd / 1e6).toFixed(2) + 'M' : (dexData?.liquidity?.usd ? (dexData.liquidity.usd / 1e6).toFixed(2) + 'M' : 'N/A')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Security + Clusters Grid */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* Security Panel */}
                <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Shield className="w-5 h-5 text-[#8B5CF6]" />
                    <h3 className="font-bold">Security Audit</h3>
                  </div>
                  <div className="space-y-2.5">
                    {[
                      { label: 'Honeypot', val: security.is_honeypot, good: security.is_honeypot === false },
                      { label: 'Can Sell', val: security.can_sell, good: security.can_sell === true },
                      { label: 'Mintable', val: security.is_mintable, good: security.is_mintable === false },
                      { label: 'Freezable', val: security.is_freezable, good: security.is_freezable === false },
                      { label: 'Buy Tax', val: security.buy_tax + '%', good: (security.buy_tax || 0) === 0 },
                      { label: 'Sell Tax', val: security.sell_tax + '%', good: (security.sell_tax || 0) === 0 },
                      { label: 'Mint Authority', val: security.mint_authority ?? 'None', good: security.mint_authority === null },
                      { label: 'Freeze Authority', val: security.freeze_authority ?? 'None', good: security.freeze_authority === null },
                      { label: 'Top 10 Holders', val: (security.top_10_holder_pct || 0).toFixed(2) + '%', good: (security.top_10_holder_pct || 0) < 30 },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-white/50">{item.label}</span>
                        <span className={`flex items-center gap-1.5 font-medium ${item.good ? 'text-emerald-400' : item.good === false ? 'text-red-400' : 'text-yellow-400'}`}>
                          {item.good === true ? <CheckCircle className="w-3.5 h-3.5" /> : item.good === false ? <XCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                          {typeof item.val === 'boolean' ? (item.val ? 'Yes' : 'No') : String(item.val ?? 'N/A')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Clusters / Wallet Groups */}
                <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Users className="w-5 h-5 text-[#28CBF4]" />
                    <h3 className="font-bold">Wallet Clusters</h3>
                  </div>
                  {clusters.length === 0 ? (
                    <div className="text-sm text-white/30 text-center py-6">No cluster data available</div>
                  ) : (
                    <div className="space-y-3">
                      {clusters.map((cluster: any) => (
                        <div key={cluster.id} className="bg-white/5 rounded-lg p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 rounded-full" style={{ background: cluster.color || '#8B5CF6' }} />
                              <span className="font-semibold text-sm">{cluster.name}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${riskColor(cluster.risk)}`}>
                                {cluster.risk || 'UNKNOWN'}
                              </span>
                            </div>
                            <span className="text-xs text-white/40">{cluster.supply_percentage?.toFixed(2) || '0'}%</span>
                          </div>
                          <div className="text-xs text-white/30 mt-1">{cluster.wallet_count || 0} wallets</div>
                          {cluster.wallets?.length > 0 && (
                            <div className="mt-2 space-y-1">
                              {cluster.wallets.slice(0, 3).map((w: any, wi: number) => (
                                <div key={wi} className="flex items-center justify-between text-xs">
                                  <span className="font-mono text-white/40">{w.address?.slice(0, 8)}...{w.address?.slice(-4)}</span>
                                  <span className="text-white/50">{w.percentage?.toFixed(2) || '0'}%</span>
                                </div>
                              ))}
                              {cluster.wallets.length > 3 && (
                                <div className="text-xs text-white/30">+{cluster.wallets.length - 3} more</div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Flags + Bundle */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* Red/Green Flags */}
                <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                  <h3 className="font-bold mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-red-400" /> Findings
                  </h3>
                  {redFlags.length === 0 && greenFlags.length === 0 ? (
                    <div className="text-sm text-white/30 text-center py-4">No findings</div>
                  ) : (
                    <div className="space-y-2">
                      {redFlags.map((f: string, i: number) => (
                        <div key={`r-${i}`} className="flex items-start gap-2 text-sm text-red-400/80 bg-red-500/10 rounded-lg p-2.5">
                          <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                          {f}
                        </div>
                      ))}
                      {greenFlags.map((f: string, i: number) => (
                        <div key={`g-${i}`} className="flex items-start gap-2 text-sm text-emerald-400/80 bg-emerald-500/10 rounded-lg p-2.5">
                          <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />
                          {f}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Bundle Analysis */}
                <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                  <h3 className="font-bold mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[#D1A340]" /> Bundle Analysis
                  </h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-white/50">Bundle Detected</span>
                      <span className={bundle.is_bundle ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                        {bundle.is_bundle ? 'YES' : 'No'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-white/50">Probability</span>
                      <span className="font-mono">{(bundle.bundle_probability || 0).toFixed(1)}%</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-white/50">Severity</span>
                      <span className={`font-bold ${(bundle.severity || '').toLowerCase() === 'high' ? 'text-red-400' : 'text-white/60'}`}>
                        {bundle.severity || 'N/A'}
                      </span>
                    </div>
                    {bundle.signals_triggered?.length > 0 && (
                      <div className="mt-2">
                        <div className="text-xs text-white/40 mb-1">Signals Triggered</div>
                        <div className="flex flex-wrap gap-1.5">
                          {bundle.signals_triggered.map((s: string, i: number) => (
                            <span key={i} className="px-2 py-0.5 bg-red-500/20 text-red-400 text-[10px] rounded font-medium">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Scan Error */}
        {scanError && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm">
            <AlertTriangle className="w-4 h-4 inline mr-2" />
            {scanError}
          </div>
        )}

        {/* Trending Tokens - PRIMARY CONTENT */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-lg flex items-center gap-2">
              <Globe className="w-5 h-5 text-[#28CBF4]" />
              Trending on {chainCfg.name}
            </h2>
            <span className="text-xs text-white/40">{trending.length} tokens</span>
          </div>

          {trendingLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-[#8B5CF6]" />
            </div>
          ) : trending.length === 0 ? (
            <div className="text-center py-12 text-white/30 text-sm">
              <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
              No trending data available for {chainCfg.name}
              <br />
              <span className="text-xs">Try another chain or search for a token</span>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {trending.map((token, i) => (
                <motion.button
                  key={token.address || i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  onClick={() => { setSearchAddr(token.address); handleScan(token.address); }}
                  className="bg-[#0e0e16] border border-white/10 hover:border-[#8B5CF6]/40 rounded-xl p-4 text-left transition-all hover:bg-white/[0.02] group"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#8B5CF6]/20 to-[#28CBF4]/20 flex items-center justify-center text-xs font-bold text-[#8B5CF6]">
                        {(token.symbol || '??').slice(0, 2)}
                      </div>
                      <div>
                        <div className="font-semibold text-sm leading-tight">{token.name || 'Unknown'}</div>
                        <div className="text-[10px] text-white/30 font-mono">{token.symbol || '???'}</div>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-[#8B5CF6] transition-colors" />
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <div className="text-xs text-white/40">Price</div>
                      <div className="font-mono text-sm font-bold">
                        ${typeof token.price_usd === 'number' ? token.price_usd.toLocaleString(undefined, { maximumFractionDigits: 8 }) : 'N/A'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-xs font-bold ${(token.price_change_24h || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {(token.price_change_24h || 0) >= 0 ? '+' : ''}{(token.price_change_24h || 0).toFixed(2)}%
                      </div>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${riskColor(token.risk_level)}`}>
                        {token.risk_level || '?'}
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-[10px] text-white/30">
                    <span>Vol: ${typeof token.volume_24h === 'number' ? (token.volume_24h / 1e3).toFixed(1) + 'K' : 'N/A'}</span>
                    <span>Liq: ${typeof token.liquidity === 'number' ? (token.liquidity / 1e3).toFixed(1) + 'K' : 'N/A'}</span>
                  </div>
                </motion.button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
