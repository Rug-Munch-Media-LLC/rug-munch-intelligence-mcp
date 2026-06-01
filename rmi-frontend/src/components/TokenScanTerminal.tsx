/**
 * TokenScanTerminal — RMI Token Scanner
 * Real SENTINEL pipeline: identity → security → liquidity → holders → honeypot
 * Handles both /crypto/full-scan (flat) and /token/scan (raw) response shapes
 */
import React, { useState, useRef, useCallback } from 'react';
import {
  Search, Shield, AlertTriangle, Skull, CheckCircle2, Clock,
  Copy, Check, Download, Loader2, Zap, Lock, Unlock,
  Droplets, Users, Flame, TrendingUp, TrendingDown, Activity,
  ExternalLink, ChevronDown, ChevronUp, RefreshCw, Brain,
  Fingerprint, Eye, ZapOff, Plus, User, XCircle, AlertCircle
} from 'lucide-react';
import { toPng } from 'html-to-image';
import api from '../services/api';

// ═══════════════════════════════════════════════════════════
// SCAN MODULES (fake progress indicators)
// ═══════════════════════════════════════════════════════════

const TOKEN_SCAN_MODULES = [
  { key: 'identity', label: 'Identifying token...', icon: Fingerprint },
  { key: 'security', label: 'Checking mint & freeze authority...', icon: Shield },
  { key: 'liquidity', label: 'Analyzing liquidity pools...', icon: Droplets },
  { key: 'holders', label: 'Analyzing holder concentration...', icon: Users },
  { key: 'honeypot', label: 'Running honeypot detection...', icon: AlertTriangle },
  { key: 'complete', label: 'Scan complete!', icon: CheckCircle2 },
];

// ═══════════════════════════════════════════════════════════
// TYPES — supports both flat (full-scan) and raw (token/scan) SENTINEL shapes
// ═══════════════════════════════════════════════════════════

interface ScanResult {
  // Identity
  token_address?: string;
  token?: string;
  chain: string;
  symbol?: string;
  name?: string;
  // Risk
  overall_risk?: string;
  risk_score: number;
  risk_level?: string;
  safety_score?: number;
  confidence?: number;
  // Flags
  mint_authority_renounced?: boolean;
  freeze_authority_renounced?: boolean;
  honeypot_detected?: boolean;
  // Liquidity
  total_liquidity_usd?: number;
  liquidity_pools?: Array<{
    dex: string;
    pair: string;
    liquidity_usd: number;
    lp_locked_percentage: number;
  }>;
  // Holders
  holder_concentration?: {
    top_10_percentage?: number;
    top_50_percentage?: number;
    total_holders?: number;
  };
  // Tax
  tax_info?: {
    buy_tax: number;
    sell_tax: number;
    transfer_tax: number;
  };
  // Flags
  red_flags?: string[];
  green_flags?: string[];
  // Timestamps
  analyzed_at?: string;
  scanned_at?: string;
  // AI
  ai_consensus?: string;
  // Raw SENTINEL fields
  risk_flags?: string[];
  free?: Record<string, any>;
  pro?: Record<string, any> | null;
  elite?: Record<string, any> | null;
  modules_analyzed?: number;
  modules_run?: string[];
  tier_required?: string;
  tier?: string;
  usage?: Record<string, any>;
  upgrade_hint?: string | null;
  status?: string;
  // Whale/Sniper enrichment
  whale_data?: { whales: any[]; total_detected: number };
  sniper_data?: { snipers: any[]; total_detected: number };
  gmgn_data?: Record<string, any>;
}

// ═══════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════

function getRiskColor(score: number): { bg: string; text: string; border: string; gradient: string; icon: any } {
  if (score >= 70) return { bg: 'bg-red-950/40', text: 'text-red-400', border: 'border-red-800/40', gradient: 'from-red-600 to-red-900', icon: Skull };
  if (score >= 40) return { bg: 'bg-orange-950/40', text: 'text-orange-400', border: 'border-orange-800/40', gradient: 'from-orange-500 to-red-600', icon: AlertTriangle };
  if (score >= 20) return { bg: 'bg-yellow-950/40', text: 'text-yellow-400', border: 'border-yellow-800/40', gradient: 'from-yellow-500 to-orange-500', icon: AlertTriangle };
  return { bg: 'bg-emerald-950/40', text: 'text-emerald-400', border: 'border-emerald-800/40', gradient: 'from-emerald-500 to-green-600', icon: CheckCircle2 };
}

function getRiskLabel(score: number): string {
  if (score >= 70) return 'CRITICAL';
  if (score >= 40) return 'HIGH RISK';
  if (score >= 20) return 'MEDIUM RISK';
  return 'SAFE';
}

function truncate(addr: string, front = 6, back = 4): string {
  if (!addr || addr.length <= front + back + 3) return addr || '';
  return `${addr.slice(0, front)}...${addr.slice(-back)}`;
}

/** Normalize both flat (full-scan) and raw (token/scan) SENTINEL responses */
function normalizeResult(raw: ScanResult): ScanResult {
  const isFlat = !!raw.risk_score && !!raw.token_address;
  if (isFlat && raw.holder_concentration?.top_10_percentage !== undefined) return raw; // already fully flat

  // Raw SENTINEL format — derive flat fields
  const free = raw.free ?? {};
  const safety = raw.safety_score ?? (raw.risk_score !== undefined ? 100 - raw.risk_score : 50);
  const risk = raw.risk_score ?? (100 - safety);
  return {
    ...raw,
    token_address: raw.token ?? raw.token_address ?? '',
    risk_score: risk,
    risk_level: raw.risk_level ?? (risk >= 70 ? 'critical' : risk >= 40 ? 'high' : risk >= 20 ? 'medium' : 'low'),
    honeypot_detected: raw.honeypot_detected ?? (free.honeypot_risk === 'high' || (free.honeypot_is?.is_honeypot ?? false)),
    mint_authority_renounced: raw.mint_authority_renounced ?? (free.mint_authority === 'renounced' || free.mint_authority == null),
    freeze_authority_renounced: raw.freeze_authority_renounced ?? (free.freeze_authority === 'renounced' || free.freeze_authority == null),
    total_liquidity_usd: raw.total_liquidity_usd ?? free.liquidity_usd ?? 0,
    liquidity_pools: raw.liquidity_pools ?? free.liquidity_pools ?? [],
    holder_concentration: raw.holder_concentration ?? free.holders ?? {},
    tax_info: raw.tax_info ?? (free.buy_tax != null || free.sell_tax != null ? { buy_tax: free.buy_tax ?? 0, sell_tax: free.sell_tax ?? 0, transfer_tax: free.transfer_tax ?? 0 } : undefined),
    red_flags: raw.red_flags ?? raw.risk_flags ?? [],
    green_flags: raw.green_flags ?? free.green_flags ?? [],
    analyzed_at: raw.analyzed_at ?? raw.scanned_at ?? new Date().toISOString(),
    ai_consensus: raw.ai_consensus ?? free.ai_consensus ?? free.rag_scam_check?.summary,
  };
}

// ═══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════

interface TokenScanTerminalProps {
  embedded?: boolean;
  defaultAddress?: string;
}

export default function TokenScanTerminal({ embedded = false, defaultAddress = '' }: TokenScanTerminalProps) {
  const [address, setAddress] = useState(defaultAddress);
  const [chain, setChain] = useState('solana');
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentModule, setCurrentModule] = useState<string>('identity');
  const [watching, setWatching] = useState(false);
  const [watchAdded, setWatchAdded] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const chains = [
    { id: 'solana', name: 'Solana', icon: '◎' },
    { id: 'ethereum', name: 'Ethereum', icon: '⧫' },
    { id: 'bsc', name: 'BSC', icon: 'B' },
    { id: 'base', name: 'Base', icon: 'B' },
    { id: 'arbitrum', name: 'Arbitrum', icon: 'A' },
  ];

  const handleScan = async () => {
    if (!address || address.length < 10) {
      setError('Enter a valid token contract address');
      return;
    }
    setError('');
    setScanning(true);
    setResult(null);
    setShowDetails(false);
    setProgress(0);
    setCurrentModule('identity');

    // Simulated progress through modules
    const moduleTimers = TOKEN_SCAN_MODULES.map((m, i) => {
      return setTimeout(() => {
        setCurrentModule(m.key);
        setProgress(Math.round(((i + 1) / TOKEN_SCAN_MODULES.length) * 100));
      }, i * 500);
    });

    try {
      // SENTINEL token scan — full pipeline with Helius enrichment
      let data;
      try {
        data = await api.fullCryptoScan(address, chain);
      } catch {
        // Fallback: direct token scan (no Helius enrichment)
        data = await api.tokenScan(address, chain);
      }
      setResult(normalizeResult(data));
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Scan failed. Try again.');
    } finally {
      moduleTimers.forEach(clearTimeout);
      setProgress(100);
      setCurrentModule('complete');
      setScanning(false);
    }
  };

  const exportCard = useCallback(async () => {
    if (!cardRef.current) return;
    setGenerating(true);
    try {
      const dataUrl = await toPng(cardRef.current, { pixelRatio: 2, backgroundColor: '#0a0a0f' });
      const link = document.createElement('a');
      link.download = `rmi-scan-${truncate(address)}.png`;
      link.href = dataUrl;
      link.click();
    } catch (e) {
      console.error('Export failed:', e);
    } finally {
      setGenerating(false);
    }
  }, [address]);

  const copyResult = () => {
    if (!result) return;
    const addr = result.token_address ?? result.token ?? '';
    const text = `🔍 RMI Scan Result\nToken: ${truncate(addr)}\nRisk: ${result.risk_score}/100 (${getRiskLabel(result.risk_score)})\nHoneypot: ${result.honeypot_detected ? 'YES 🍯' : 'No'}\nMint: ${result.mint_authority_renounced ? 'Renounced ✅' : 'NOT Renounced ❌'}\nLP Locked: ${result.liquidity_pools?.some(p => p.lp_locked_percentage > 80) ? 'Yes ✅' : 'No ❌'}\n\nScan by @rugmunchbot`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleWatchToken = async () => {
    if (!result) return;
    const addr = result.token_address ?? result.token ?? '';
    if (!addr) return;
    setWatching(true);
    try {
      await api.client.post('/api/v1/watchlist', {
        user_id: 'local',
        address: addr,
        type: 'Token',
        chain: result.chain || chain,
        tags: [`risk:${result.risk_score}`, result.honeypot_detected ? 'honeypot' : 'clean'].filter(Boolean),
      });
    } catch {
      // API may not exist yet; persist locally anyway
    }
    // Also persist to localStorage fallback
    const stored = localStorage.getItem('rmi_watchlist');
    const items = stored ? JSON.parse(stored) : [];
    if (!items.find((i: any) => i.address === addr)) {
      items.unshift({
        address: addr,
        type: 'Token',
        chain: result.chain || chain,
        risk_score: result.risk_score,
        tags: [`risk:${result.risk_score}`],
        added_at: new Date().toISOString(),
      });
      localStorage.setItem('rmi_watchlist', JSON.stringify(items));
    }
    setWatchAdded(true);
    setWatching(false);
  };

  const riskColors = result ? getRiskColor(result.risk_score) : getRiskColor(0);
  const RiskIcon = riskColors.icon;

  return (
    <div className={`${embedded ? '' : 'min-h-screen bg-[#0a0a0f] text-slate-200 py-8'}`}>
      <div className={`${embedded ? '' : 'max-w-3xl mx-auto px-4 sm:px-6'}`}>
        {!embedded && (
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded bg-purple-950/60 border border-purple-800/40 flex items-center justify-center">
                <Shield className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Token Scanner</h1>
                <p className="text-xs text-purple-400/70 font-mono tracking-wider uppercase">28+ data sources • Real-time analysis</p>
              </div>
            </div>
          </div>
        )}

        {/* INPUT */}
        <div className="bg-slate-900/60 border border-slate-800/60 rounded-xl p-4 mb-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={address}
                onChange={e => setAddress(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleScan()}
                placeholder="Paste token contract address..."
                className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-600/50"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={chain}
                onChange={e => setChain(e.target.value)}
                className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-3 text-sm text-slate-300 focus:outline-none focus:border-purple-600/50"
              >
                {chains.map(c => (
                  <option key={c.id} value={c.id}>{c.icon} {c.name}</option>
                ))}
              </select>
              <button
                onClick={handleScan}
                disabled={scanning || !address}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-bold rounded-lg flex items-center gap-2 transition-colors"
              >
                {scanning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Scan
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ERROR */}
        {error && (
          <div className="bg-red-950/30 border border-red-800/40 rounded-xl p-4 mb-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-300 text-sm font-medium">{error}</p>
              {error.includes('limit') && (
                <p className="text-red-400/70 text-xs mt-1">Free tier: 5 scans/day. Upgrade for more.</p>
              )}
            </div>
          </div>
        )}

        {/* PROGRESS */}
        {scanning && (
          <div className="bg-slate-900/60 border border-slate-800/60 rounded-xl p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              {(() => {
                const mod = TOKEN_SCAN_MODULES.find(m => m.key === currentModule) ?? TOKEN_SCAN_MODULES[0];
                const ModIcon = mod.icon;
                return <ModIcon className="w-4 h-4 text-purple-400" />;
              })()}
              <span className="text-sm text-slate-300">
                {TOKEN_SCAN_MODULES.find(m => m.key === currentModule)?.label ?? 'Scanning...'}
              </span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-600 to-purple-400 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* RESULT CARD */}
        {result && !scanning && (
          <div ref={cardRef} className="bg-gradient-to-br from-slate-900 via-slate-900 to-purple-950/20 border border-slate-800/60 rounded-xl overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-900/40 to-transparent p-4 border-b border-slate-800/40">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded bg-purple-950/60 border border-purple-800/40 flex items-center justify-center">
                    <Shield className="w-4 h-4 text-purple-400" />
                  </div>
                  <span className="text-white/90 text-xs font-bold tracking-wider">SECURITY SCAN</span>
                </div>
                <span className="text-white/60 text-[10px]">{new Date(result.analyzed_at ?? result.scanned_at ?? '').toLocaleString()}</span>
              </div>

              <div className="flex items-center gap-4">
                {/* Risk Score */}
                <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${riskColors.gradient} flex items-center justify-center shadow-lg`}>
                  <div className="text-center">
                    <div className={`text-3xl font-bold ${riskColors.text}`}>{result.risk_score}</div>
                    <div className="text-white/60 text-[9px] uppercase tracking-wider">Risk</div>
                  </div>
                </div>
                <div>
                  <div className={`text-xl font-bold ${riskColors.text}`}>{getRiskLabel(result.risk_score)}</div>
                  <div className="text-white/70 text-xs">Risk Score / 100</div>
                  <div className="text-white/50 text-[10px] mt-0.5">{truncate(result.token_address ?? result.token ?? '')} • {result.chain.toUpperCase()}</div>
                  {result.symbol && (
                    <div className="text-purple-400/80 text-[10px] mt-0.5">{result.symbol}{result.name ? ` — ${result.name}` : ''}</div>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 border-b border-slate-800/40">
              <StatBox
                icon={result.honeypot_detected ? Flame : Shield}
                label="Honeypot"
                value={result.honeypot_detected ? 'YES' : 'No'}
                danger={!!result.honeypot_detected}
              />
              <StatBox
                icon={result.mint_authority_renounced ? Lock : Unlock}
                label="Mint Auth"
                value={result.mint_authority_renounced ? 'Renounced' : 'Active'}
                danger={result.mint_authority_renounced === false || result.mint_authority_renounced === undefined}
              />
              <StatBox
                icon={Droplets}
                label="Liquidity"
                value={`$${((result.total_liquidity_usd ?? 0) / 1000).toFixed(1)}K`}
                danger={(result.total_liquidity_usd ?? 0) < 10000}
              />
              <StatBox
                icon={Users}
                label="Holders"
                value={result.holder_concentration?.total_holders?.toLocaleString() ?? 'N/A'}
                danger={false}
              />
            </div>

            {/* Liquidity Pools */}
            {result.liquidity_pools && result.liquidity_pools.length > 0 && (
              <div className="p-4 border-b border-slate-800/40">
                <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                  <Droplets className="w-3.5 h-3.5" /> Liquidity Pools
                </div>
                <div className="space-y-2">
                  {result.liquidity_pools.map((pool, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-800/30 rounded p-2">
                      <div className="flex items-center gap-2">
                        <span className="text-white text-xs font-medium">{pool.dex}</span>
                        <span className="text-slate-500 text-[10px]">{pool.pair}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-white/80 text-xs">${(pool.liquidity_usd / 1000).toFixed(1)}K</span>
                        <span className={`text-[10px] ${pool.lp_locked_percentage > 80 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {pool.lp_locked_percentage}% locked
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tax Info */}
            {result.tax_info && (
              <div className="p-4 border-b border-slate-800/40">
                <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5" /> Tax Info
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <div className="text-slate-500 text-[10px]">Buy Tax</div>
                    <div className={`text-sm font-bold ${result.tax_info.buy_tax > 10 ? 'text-red-400' : 'text-emerald-400'}`}>{result.tax_info.buy_tax}%</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-[10px]">Sell Tax</div>
                    <div className={`text-sm font-bold ${result.tax_info.sell_tax > 10 ? 'text-red-400' : 'text-emerald-400'}`}>{result.tax_info.sell_tax}%</div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-[10px]">Transfer Tax</div>
                    <div className={`text-sm font-bold ${result.tax_info.transfer_tax > 5 ? 'text-red-400' : 'text-emerald-400'}`}>{result.tax_info.transfer_tax}%</div>
                  </div>
                </div>
              </div>
            )}

            {/* Holder Concentration */}
            {result.holder_concentration && (
              <div className="p-4 border-b border-slate-800/40">
                <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5" /> Holder Concentration
                </div>
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                      <span>Top 10 Holders</span>
                      <span>{result.holder_concentration.top_10_percentage ?? 'N/A'}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${(result.holder_concentration.top_10_percentage ?? 0) > 50 ? 'bg-red-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(result.holder_concentration.top_10_percentage ?? 0, 100)}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                      <span>Top 50 Holders</span>
                      <span>{result.holder_concentration.top_50_percentage ?? 'N/A'}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${(result.holder_concentration.top_50_percentage ?? 0) > 80 ? 'bg-red-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(result.holder_concentration.top_50_percentage ?? 0, 100)}%` }} />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Red/Green Flags */}
            <div className="grid sm:grid-cols-2 gap-3 p-4">
              {(result.red_flags ?? []).length > 0 && (
                <div className="bg-red-950/20 border border-red-900/30 rounded-lg p-3">
                  <div className="text-xs font-bold text-red-400 mb-2 flex items-center gap-1.5">
                    <Flame className="w-3.5 h-3.5" /> Red Flags
                  </div>
                  <div className="space-y-1">
                    {(result.red_flags ?? []).map((flag, i) => (
                      <div key={i} className="text-[11px] text-red-300/80 flex items-start gap-1.5">
                        <span className="text-red-500 mt-0.5">•</span> {flag}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {(result.green_flags ?? []).length > 0 && (
                <div className="bg-emerald-950/20 border border-emerald-900/30 rounded-lg p-3">
                  <div className="text-xs font-bold text-emerald-400 mb-2 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Green Flags
                  </div>
                  <div className="space-y-1">
                    {(result.green_flags ?? []).map((flag, i) => (
                      <div key={i} className="text-[11px] text-emerald-300/80 flex items-start gap-1.5">
                        <span className="text-emerald-500 mt-0.5">•</span> {flag}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* AI Consensus */}
            {result.ai_consensus && (
              <div className="p-4 border-t border-slate-800/40">
                <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                  <Brain className="w-3.5 h-3.5" /> AI Consensus
                </div>
                <p className="text-white/70 text-xs leading-relaxed">{result.ai_consensus}</p>
              </div>
            )}

            {/* Whale/Sniper data if available */}
            {result.whale_data && result.whale_data.total_detected > 0 && (
              <div className="p-4 border-t border-slate-800/40">
                <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5" /> Whale Activity ({result.whale_data.total_detected} detected)
                </div>
              </div>
            )}

            {/* Module Health */}
            {result.modules_run && result.modules_run.length > 0 && (
              <div className="p-4 border-t border-slate-800/40">
                <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Module Health ({result.modules_run.length} modules)
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                  {result.modules_run.map((mod, i) => {
                    // Check if module errored: if result has errors or module status indicates degraded
                    const isOk = typeof mod === 'string' ? !mod.includes('error') && !mod.includes('fail') : true;
                    return (
                      <div key={i} className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] ${isOk ? 'bg-emerald-950/20 text-emerald-300' : 'bg-red-950/20 text-red-300'}`}>
                        {isOk ? <CheckCircle2 className="w-3 h-3 text-emerald-500" /> : <XCircle className="w-3 h-3 text-red-500" />}
                        <span>{typeof mod === 'string' ? mod : String(mod)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Module Count Warning */}
            {result.modules_analyzed !== undefined && result.modules_analyzed < 21 && (
              <div className="px-4 py-2.5 border-t border-slate-800/40 bg-yellow-950/10">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                  <p className="text-xs text-yellow-300">
                    {result.modules_analyzed}/21 modules completed — some data may be incomplete
                  </p>
                </div>
              </div>
            )}

            {/* Dev Reputation / Dev Profile */}
            {(result as any).dev_reputation && (
              <div className="p-4 border-t border-slate-800/40">
                <div className="text-xs font-bold text-slate-400 mb-2 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5" /> Dev Profile
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {((result as any).dev_reputation.wallet_address || (result as any).dev_reputation.dev_wallet) && (
                    <div>
                      <div className="text-[10px] text-slate-500">Wallet</div>
                      <div className="text-xs text-white/80 font-mono truncate">
                        {truncate((result as any).dev_reputation.wallet_address || (result as any).dev_reputation.dev_wallet)}
                      </div>
                    </div>
                  )}
                  {((result as any).dev_reputation.previous_rugs !== undefined || (result as any).dev_reputation.rugs !== undefined) && (
                    <div>
                      <div className="text-[10px] text-slate-500">Previous Rugs</div>
                      <div className={`text-sm font-bold ${((result as any).dev_reputation.previous_rugs ?? (result as any).dev_reputation.rugs) > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                        {(result as any).dev_reputation.previous_rugs ?? (result as any).dev_reputation.rugs ?? 0}
                      </div>
                    </div>
                  )}
                  {((result as any).dev_reputation.reputation_score !== undefined || (result as any).dev_reputation.score !== undefined) && (
                    <div>
                      <div className="text-[10px] text-slate-500">Reputation</div>
                      <div className="text-sm font-bold text-purple-400">
                        {(result as any).dev_reputation.reputation_score ?? (result as any).dev_reputation.score}/100
                      </div>
                    </div>
                  )}
                  {((result as any).dev_reputation.cross_chain_connections || (result as any).dev_reputation.chains) && (
                    <div>
                      <div className="text-[10px] text-slate-500">Cross-Chain</div>
                      <div className="text-xs text-white/80">
                        {Array.isArray((result as any).dev_reputation.cross_chain_connections)
                          ? (result as any).dev_reputation.cross_chain_connections.join(', ')
                          : Array.isArray((result as any).dev_reputation.chains)
                            ? (result as any).dev_reputation.chains.join(', ')
                            : 'N/A'}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="p-4 border-t border-slate-800/40 flex items-center gap-2 flex-wrap">
              <button
                onClick={copyResult}
                className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1.5 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                onClick={exportCard}
                disabled={generating}
                className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                {generating ? 'Generating...' : 'Export PNG'}
              </button>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1.5 transition-colors"
              >
                {showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                Raw JSON
              </button>
              <button
                onClick={handleWatchToken}
                disabled={watchAdded || watching}
                className={`px-3 py-1.5 text-xs rounded-lg flex items-center gap-1.5 transition-colors ${
                  watchAdded
                    ? 'bg-emerald-950/30 border border-emerald-800/40 text-emerald-400'
                    : 'bg-purple-600/40 hover:bg-purple-600/60 border border-purple-800/40 text-purple-300'
                } disabled:opacity-70`}
              >
                {watching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : watchAdded ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
                {watchAdded ? 'Watching' : 'Watch Token'}
              </button>
            </div>

            {/* Raw JSON Details */}
            {showDetails && (
              <div className="border-t border-slate-800/40 p-4">
                <pre className="text-[10px] text-slate-400 overflow-x-auto whitespace-pre-wrap bg-slate-950/50 rounded p-3 max-h-64">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!result && !scanning && !error && (
          <div className="bg-slate-900/30 border border-slate-800/30 rounded-xl p-8 text-center">
            <Shield className="w-12 h-12 text-purple-500/30 mx-auto mb-3" />
            <p className="text-slate-400 text-sm">Paste a token address and hit Scan</p>
            <p className="text-slate-500 text-xs mt-1">28+ data sources for real-time risk analysis</p>
          </div>
        )}
      </div>
    </div>
  );
}

function StatBox({ icon: Icon, label, value, danger }: { icon: any; label: string; value: string; danger: boolean }) {
  return (
    <div className={`rounded-lg p-2.5 ${danger ? 'bg-red-950/20 border border-red-900/30' : 'bg-slate-800/30 border border-slate-700/30'}`}>
      <Icon className={`w-4 h-4 mb-1 ${danger ? 'text-red-400' : 'text-slate-500'}`} />
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className={`text-sm font-bold ${danger ? 'text-red-400' : 'text-white/90'}`}>{value}</div>
    </div>
  );
}