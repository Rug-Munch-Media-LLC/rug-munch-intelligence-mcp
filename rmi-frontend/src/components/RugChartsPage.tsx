import { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import {
  Search, TrendingUp, TrendingDown, Shield, AlertTriangle, CheckCircle,
  Loader2, ExternalLink, BarChart3, Activity, Zap, Copy, Check,
  ChevronRight, RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const CHAINS = [
  { id: 'solana', name: 'Solana', icon: 'S', explorer: 'https://solscan.io/token/', color: '#9945FF' },
  { id: 'base', name: 'Base', icon: 'B', explorer: 'https://basescan.org/token/', color: '#0052FF' },
  { id: 'ethereum', name: 'Ethereum', icon: 'E', explorer: 'https://etherscan.io/token/', color: '#627EEA' },
  { id: 'bsc', name: 'BSC', icon: 'BNB', explorer: 'https://bscscan.com/token/', color: '#F0B90B' },
];

const API_BASE = '';

export default function RugChartsPage() {
  const setCurrentPage = useAppStore((s) => s.setCurrentPage);

  const [chain, setChain] = useState('solana');
  const [searchAddr, setSearchAddr] = useState('');
  const [trending, setTrending] = useState<any[]>([]);
  const [trendingLoading, setTrendingLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<any | null>(null);
  const [signals, setSignals] = useState<any | null>(null);
  const [ohlcv, setOhlcv] = useState<any[]>([]);
  const [ohlcvLoading, setOhlcvLoading] = useState(false);
  const [dexData, setDexData] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchTrending = useCallback(async () => {
    setTrendingLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/rugcharts/trending?chain=${chain}&limit=12`);
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
    setScanResult(null);
    setSignals(null);
    setOhlcv([]);
    setDexData(null);

    try {
      const [scanRes, sigRes, ohlcvRes, dexRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/rugmaps/scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address: target, chain }),
        }),
        fetch(`${API_BASE}/api/v1/rugcharts/signals/${target}`).catch(() => null),
        fetch(`${API_BASE}/api/v1/tokens/${target}/ohlcv?timeframe=1H&limit=48`).catch(() => null),
        fetch(`https://api.dexscreener.com/latest/dex/tokens/${target}`).catch(() => null),
      ]);

      const scanData = await scanRes.json().catch(() => null);
      if (scanData?.success && scanData.data) {
        setScanResult(scanData.data);
      } else if (scanData && typeof scanData === 'object') {
        setScanResult(scanData);
      }

      const sigData = sigRes ? await sigRes.json().catch(() => null) : null;
      if (sigData) setSignals(sigData);

      const ohlcvData = ohlcvRes ? await ohlcvRes.json().catch(() => null) : null;
      if (ohlcvData?.data && Array.isArray(ohlcvData.data)) {
        setOhlcv(ohlcvData.data);
      }

      const dexJson = dexRes ? await dexRes.json().catch(() => null) : null;
      if (dexJson?.pairs?.length) setDexData(dexJson.pairs[0]);
    } catch (e: any) {
      console.error('Scan error:', e);
    } finally {
      setScanning(false);
    }
  };

  const copyAddress = (addr: string) => {
    navigator.clipboard.writeText(addr);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const riskColor = (level?: string) => {
    const l = (level || '').toLowerCase();
    if (l.includes('critical')) return 'bg-red-600 text-white';
    if (l.includes('high')) return 'bg-orange-500 text-white';
    if (l.includes('medium')) return 'bg-yellow-500 text-black';
    if (l.includes('low') || l.includes('safe')) return 'bg-emerald-500 text-white';
    return 'bg-gray-500 text-white';
  };

  const changeColor = (val: number) => val >= 0 ? 'text-emerald-400' : 'text-red-400';

  const chainCfg = CHAINS.find((c) => c.id === chain) || CHAINS[0];
  const token = scanResult?.token || {};
  const market = scanResult?.market || {};
  const security = scanResult?.security || {};
  const findings = scanResult?.findings || {};

  return (
    <div className="min-h-screen bg-[#07070b] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#0e0e16]/80 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-[1400px] mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#28CBF4] to-[#8B5CF6] flex items-center justify-center font-bold text-lg">
              RC
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight">RugCharts</h1>
              <p className="text-xs text-white/40">AI Forensic Analysis & Price Intelligence</p>
            </div>
          </div>
          <div className="flex gap-1 bg-white/5 rounded-lg p-1">
            {CHAINS.map((c) => (
              <button
                key={c.id}
                onClick={() => { setChain(c.id); setScanResult(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  chain === c.id ? 'bg-[#28CBF4] text-black' : 'text-white/50 hover:text-white hover:bg-white/5'
                }`}
              >
                {c.icon}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-6 py-6 grid lg:grid-cols-[1fr_300px] gap-6">
        {/* Main Content */}
        <div className="space-y-6">
          {/* Search */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
              <input
                value={searchAddr}
                onChange={(e) => setSearchAddr(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleScan()}
                placeholder="Enter token address to analyze..."
                className="w-full bg-[#0e0e16] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:border-[#28CBF4] placeholder:text-white/20"
              />
            </div>
            <button
              onClick={() => handleScan()}
              disabled={scanning || !searchAddr.trim()}
              className="px-6 py-3 bg-[#28CBF4] hover:bg-[#1DBBD5] disabled:opacity-40 rounded-xl font-semibold text-sm text-black flex items-center gap-2 transition-colors"
            >
              {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              Analyze
            </button>
          </motion.div>

          {/* Scan Results */}
          <AnimatePresence>
            {scanResult && (
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-4">
                {/* Token Header */}
                <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold" style={{ background: chainCfg.color + '20', color: chainCfg.color }}>
                        {(token.symbol || '??').slice(0, 2)}
                      </div>
                      <div>
                        <h2 className="text-xl font-bold">{token.name || 'Unknown Token'}</h2>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm text-white/50 font-mono">{token.address || searchAddr}</span>
                          <button onClick={() => copyAddress(token.address || searchAddr)} className="text-white/30 hover:text-white/60">
                            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                          <a href={chainCfg.explorer + (token.address || searchAddr)} target="_blank" rel="noopener noreferrer" className="text-[#28CBF4] hover:text-[#5EE0FF]">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${riskColor(scanResult.risk_level)}`}>
                        {scanResult.risk_level || 'UNKNOWN'}
                      </span>
                      <div className="text-sm text-white/40 mt-1">Score: {scanResult.risk_score ?? 'N/A'}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5">
                    {[
                      { label: 'Price', val: `$${(market.price_usd || dexData?.priceUsd || 0).toLocaleString()}` },
                      { label: '24h Change', val: `${(market.price_change_24h || 0) >= 0 ? '+' : ''}${(market.price_change_24h || 0).toFixed(2)}%`, color: changeColor(market.price_change_24h || 0) },
                      { label: 'Volume 24h', val: `$${((market.volume_24h || 0) / 1e6).toFixed(2)}M` },
                      { label: 'Market Cap', val: `$${((market.market_cap || 0) / 1e6).toFixed(2)}M` },
                    ].map((item, i) => (
                      <div key={i} className="bg-white/5 rounded-lg p-3">
                        <div className="text-xs text-white/40">{item.label}</div>
                        <div className={`font-mono text-lg font-bold ${item.color || ''}`}>{item.val}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Price History (OHLCV Table) */}
                <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-[#28CBF4]" />
                      Price History (1H)
                    </h3>
                    <span className="text-xs text-white/40">{ohlcv.length} candles</span>
                  </div>
                  {ohlcv.length === 0 ? (
                    <div className="text-center py-8 text-white/30 text-sm">
                      <Activity className="w-6 h-6 mx-auto mb-2 opacity-50" />
                      No OHLCV data available
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-white/40 border-b border-white/10">
                            <th className="text-left py-2 px-2">Time</th>
                            <th className="text-right py-2 px-2">Open</th>
                            <th className="text-right py-2 px-2">High</th>
                            <th className="text-right py-2 px-2">Low</th>
                            <th className="text-right py-2 px-2">Close</th>
                            <th className="text-right py-2 px-2">Volume</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ohlcv.slice(-20).reverse().map((c: any, i: number) => (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                              <td className="py-2 px-2 font-mono text-white/50">{new Date(c.time * 1000).toLocaleTimeString()}</td>
                              <td className="py-2 px-2 text-right font-mono">${c.open?.toLocaleString()}</td>
                              <td className="py-2 px-2 text-right font-mono text-emerald-400">${c.high?.toLocaleString()}</td>
                              <td className="py-2 px-2 text-right font-mono text-red-400">${c.low?.toLocaleString()}</td>
                              <td className={`py-2 px-2 text-right font-mono font-bold ${c.close >= c.open ? 'text-emerald-400' : 'text-red-400'}`}>
                                ${c.close?.toLocaleString()}
                              </td>
                              <td className="py-2 px-2 text-right font-mono text-white/50">{c.volume?.toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Security + Signals */}
                <div className="grid md:grid-cols-2 gap-4">
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
                        { label: 'Buy Tax', val: (security.buy_tax || 0) + '%', good: (security.buy_tax || 0) === 0 },
                        { label: 'Sell Tax', val: (security.sell_tax || 0) + '%', good: (security.sell_tax || 0) === 0 },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <span className="text-white/50">{item.label}</span>
                          <span className={`flex items-center gap-1.5 font-medium ${item.good ? 'text-emerald-400' : item.good === false ? 'text-red-400' : 'text-yellow-400'}`}>
                            {item.good === true ? <CheckCircle className="w-3.5 h-3.5" /> : item.good === false ? <AlertTriangle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                            {typeof item.val === 'boolean' ? (item.val ? 'Yes' : 'No') : String(item.val ?? 'N/A')}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <Activity className="w-5 h-5 text-[#D1A340]" />
                      <h3 className="font-bold">Technical Signals</h3>
                    </div>
                    {signals ? (
                      <div className="space-y-2">
                        {Object.entries(signals).slice(0, 8).map(([key, val]: [string, any]) => (
                          <div key={key} className="flex items-center justify-between text-sm">
                            <span className="text-white/50 capitalize">{key.replace(/_/g, ' ')}</span>
                            <span className={`font-mono text-xs ${val === true ? 'text-emerald-400' : val === false ? 'text-white/30' : typeof val === 'number' ? (val > 0 ? 'text-emerald-400' : 'text-red-400') : 'text-white/60'}`}>
                              {typeof val === 'boolean' ? (val ? 'Yes' : 'No') : typeof val === 'number' ? val.toFixed(2) : String(val ?? 'N/A')}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-white/30 text-sm">No signal data</div>
                    )}
                  </div>
                </div>

                {/* Findings */}
                {((findings.red_flags?.length || 0) + (findings.green_flags?.length || 0)) > 0 && (
                  <div className="bg-[#0e0e16] border border-white/10 rounded-xl p-5">
                    <h3 className="font-bold mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-red-400" /> Findings
                    </h3>
                    <div className="space-y-2">
                      {(findings.red_flags || []).map((f: string, i: number) => (
                        <div key={`r-${i}`} className="flex items-start gap-2 text-sm text-red-400/80 bg-red-500/10 rounded-lg p-2.5">
                          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />{f}
                        </div>
                      ))}
                      {(findings.green_flags || []).map((f: string, i: number) => (
                        <div key={`g-${i}`} className="flex items-start gap-2 text-sm text-emerald-400/80 bg-emerald-500/10 rounded-lg p-2.5">
                          <CheckCircle className="w-4 h-4 mt-0.5 shrink-0" />{f}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Sidebar - Trending */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[#28CBF4]" />
              Trending
            </h3>
            <button onClick={fetchTrending} className="text-white/30 hover:text-white/60">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {trendingLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-[#28CBF4]" /></div>
          ) : trending.length === 0 ? (
            <div className="text-center py-8 text-white/30 text-sm">No trending data</div>
          ) : (
            <div className="space-y-2">
              {trending.map((token, i) => (
                <button
                  key={token.address || i}
                  onClick={() => { setSearchAddr(token.address); handleScan(token.address); }}
                  className="w-full bg-[#0e0e16] border border-white/10 hover:border-[#28CBF4]/40 rounded-xl p-3 text-left transition-all hover:bg-white/[0.02] group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#28CBF4]/20 to-[#8B5CF6]/20 flex items-center justify-center text-[10px] font-bold text-[#28CBF4]">
                        {(token.symbol || '??').slice(0, 2)}
                      </div>
                      <div>
                        <div className="font-semibold text-sm">{token.name || 'Unknown'}</div>
                        <div className="text-[10px] text-white/30">{token.symbol || '???'}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-xs font-bold ${(token.price_change_24h || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {(token.price_change_24h || 0) >= 0 ? '+' : ''}{(token.price_change_24h || 0).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-[10px] text-white/30">
                    <span>${typeof token.price_usd === 'number' ? token.price_usd.toLocaleString(undefined, { maximumFractionDigits: 6 }) : 'N/A'}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${riskColor(token.risk_level)}`}>
                      {token.risk_level || '?'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
