/**
 * WalletScanTerminal — RMI Wallet Scanner
 * Full wallet forensics: networth, PnL, smart money, labels, suspicious activity
 * Integrates with /api/v1/wallet/{address}/analysis, gmgn-v2, helius, wallet-label
 */
import React, { useState, useRef, useCallback } from 'react';
import {
  Search, Shield, AlertTriangle, CheckCircle2, Skull, Clock,
  Copy, Check, Download, Loader2, Zap, Eye, Wallet,
  TrendingUp, TrendingDown, Users, Activity, ExternalLink,
  ChevronDown, ChevronUp, RefreshCw, Brain, DollarSign,
  BarChart3, Layers, Flag, Fingerprint, ArrowRight
} from 'lucide-react';
import { toPng } from 'html-to-image';
import api from '../services/api';

// ── Types ──────────────────────────────────────────────────────────────────

interface WalletScanResult {
  address: string;
  chain: string;

  // Risk
  risk_score: number;
  risk_level: string;
  persona: string;
  persona_confidence: number;

  // Balance & worth
  balance_sol?: number;
  networth_usd?: number;
  total_pnl_usd?: number;
  total_pnl_pct?: number;

  // Smart money
  is_smart_money?: boolean;
  smart_money_label?: string;

  // Activity
  tx_count_recent?: number;
  tx_frequency?: number;
  success_rate?: number;
  token_count?: number;
  last_active?: string;

  // Labels & flags
  labels?: string[];
  flags?: string[];
  suspicious_flags?: Array<{
    type: string;
    description: string;
    severity: string;
    timestamp?: string;
  }>;

  // Sources
  sources_used: string[];
  analyzed_at: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function getRiskColor(score: number) {
  if (score >= 70) return { bg: 'bg-red-950/40', text: 'text-red-400', border: 'border-red-800/40', gradient: 'from-red-600 to-red-900', icon: Skull };
  if (score >= 40) return { bg: 'bg-orange-950/40', text: 'text-orange-400', border: 'border-orange-800/40', gradient: 'from-orange-500 to-red-600', icon: AlertTriangle };
  if (score >= 20) return { bg: 'bg-yellow-950/40', text: 'text-yellow-400', border: 'border-yellow-800/40', gradient: 'from-yellow-500 to-orange-500', icon: AlertTriangle };
  return { bg: 'bg-emerald-950/40', text: 'text-emerald-400', border: 'border-emerald-800/40', gradient: 'from-emerald-500 to-green-600', icon: CheckCircle2 };
}

function getRiskLabel(score: number): string {
  if (score >= 70) return 'DANGEROUS';
  if (score >= 40) return 'HIGH RISK';
  if (score >= 20) return 'MEDIUM RISK';
  return 'LOW RISK';
}

function getPersonaLabel(p: string): string {
  const map: Record<string, string> = {
    bot: 'Bot / Automation',
    active_trader: 'Active Trader',
    whale: 'Whale',
    experienced: 'Experienced',
    collector: 'Token Collector',
    casual: 'Casual User',
    inactive: 'Inactive',
    unknown: 'Unknown',
  };
  return map[p] || p;
}

function truncate(addr: string, front = 6, back = 4): string {
  if (!addr || addr.length <= front + back + 3) return addr;
  return `${addr.slice(0, front)}...${addr.slice(-back)}`;
}

function formatUSD(v: number | undefined): string {
  if (v === undefined || v === null) return 'N/A';
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`;
  return `$${v.toFixed(2)}`;
}

// ── Scan progress modules ──────────────────────────────────────────────────

const SCAN_MODULES = [
  { key: 'identity', label: 'Identifying wallet...', icon: Fingerprint },
  { key: 'balance', label: 'Checking balance & networth...', icon: Wallet },
  { key: 'pnl', label: 'Calculating PnL...', icon: TrendingUp },
  { key: 'smart_money', label: 'Smart money analysis...', icon: Brain },
  { key: 'activity', label: 'Analyzing transaction patterns...', icon: Activity },
  { key: 'labels', label: 'Checking labels & risk flags...', icon: Flag },
  { key: 'complete', label: 'Scan complete!', icon: CheckCircle2 },
];

// ── Main Component ─────────────────────────────────────────────────────────

interface WalletScanTerminalProps {
  embedded?: boolean;
  defaultAddress?: string;
}

export default function WalletScanTerminal({ embedded = false, defaultAddress = '' }: WalletScanTerminalProps) {
  const [address, setAddress] = useState(defaultAddress);
  const [chain, setChain] = useState('solana');
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<WalletScanResult | null>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentModule, setCurrentModule] = useState<string>('identity');
  const cardRef = useRef<HTMLDivElement>(null);

  const chains = [
    { id: 'solana', name: 'Solana', icon: '◎' },
    { id: 'ethereum', name: 'Ethereum', icon: '⧫' },
    { id: 'bsc', name: 'BSC', icon: 'B' },
    { id: 'base', name: 'Base', icon: '⧫' },
    { id: 'arbitrum', name: 'Arbitrum', icon: 'A' },
    { id: 'polygon', name: 'Polygon', icon: '⬡' },
  ];

  const handleScan = async () => {
    if (!address || address.length < 10) {
      setError('Enter a valid wallet address');
      return;
    }
    setError('');
    setScanning(true);
    setResult(null);
    setShowDetails(false);
    setProgress(0);
    setCurrentModule('identity');

    // Simulated progress through modules
    const moduleTimers = SCAN_MODULES.map((m, i) => {
      return setTimeout(() => {
        setCurrentModule(m.key);
        setProgress(Math.round(((i + 1) / SCAN_MODULES.length) * 100));
      }, i * 400);
    });

    try {
      // Primary: wallet full analysis (Birdeye networth + PnL + smart money)
      let data: WalletScanResult | null = null;
      try {
        const analysis = await api.client.get(`/api/v1/wallet/${address}/analysis`, { params: { chain } });
        data = {
          address: address,
          chain,
          risk_score: 0,
          risk_level: 'LOW',
          persona: analysis.data?.persona || 'unknown',
          persona_confidence: analysis.data?.persona_confidence || 0,
          networth_usd: analysis.data?.networth?.total_usd || analysis.data?.networth?.usd,
          total_pnl_usd: analysis.data?.pnl?.total_pnl_usd || analysis.data?.pnl?.pnl_usd,
          total_pnl_pct: analysis.data?.pnl?.total_pnl_pct || analysis.data?.pnl?.pnl_pct,
          is_smart_money: analysis.data?.smart_money_status?.is_smart_money,
          smart_money_label: analysis.data?.smart_money_status?.label,
          tx_count_recent: analysis.data?.networth?.tx_count,
          sources_used: ['birdeye'],
          analyzed_at: new Date().toISOString(),
        };
      } catch {
        // Fallback to gmgn wallet intelligence
        try {
          const gmgn = await api.client.post('/api/v1/gmgn-v2/wallet-intelligence', { chain, wallet_address: address });
          const gd = gmgn.data?.data || {};
          data = {
            address,
            chain,
            risk_score: gd.risk_score || 0,
            risk_level: gd.risk_level || 'LOW',
            persona: gd.persona || 'unknown',
            persona_confidence: gd.confidence || 0,
            total_pnl_usd: gd.pnl?.total_usd,
            total_pnl_pct: gd.pnl?.total_pct,
            labels: gd.tags || [],
            sources_used: ['gmgn'],
            analyzed_at: new Date().toISOString(),
          };
        } catch {
          // Final fallback: basic wallet scan
          try {
            const scan = await api.client.post('/api/v1/wallet/scan', { address, chain });
            data = {
              address,
              chain,
              risk_score: 0,
              risk_level: 'LOW',
              persona: 'unknown',
              persona_confidence: 0,
              ...(scan.data || {}),
              sources_used: scan.data?.helius ? ['helius'] : [],
              analyzed_at: new Date().toISOString(),
            };
          } catch (e2) {
            throw e2;
          }
        }
      }

      // Enrichment: wallet label (suspicious activity)
      try {
        const labelResp = await api.client.get(`/api/v1/wallet-label/${address}`, { params: { chain } });
        if (labelResp.data?.data) {
          const ld = labelResp.data.data;
          data = {
            ...data!,
            labels: [...(data!.labels || []), ...(ld.tags || [])],
            risk_score: Math.max(data!.risk_score, ld.risk_score || 0),
            risk_level: ld.risk_level || data!.risk_level,
          };
          data!.sources_used.push('wallet_memory');
        }
      } catch { /* optional */ }

      // Enrichment: suspicious transfers
      try {
        const suspResp = await api.client.get(`/api/v1/suspicious-transfers/wallet/${address}`);
        if (suspResp.data?.flags?.length) {
          data = {
            ...data!,
            suspicious_flags: suspResp.data.flags.slice(0, 10),
            risk_score: Math.min(100, data!.risk_score + suspResp.data.flags.length * 5),
          };
          data!.sources_used.push('suspicious_transfers');
        }
      } catch { /* optional */ }

      // Recalculate risk level after enrichment
      if (data!.risk_score >= 70) data!.risk_level = 'DANGEROUS';
      else if (data!.risk_score >= 40) data!.risk_level = 'HIGH';
      else if (data!.risk_score >= 20) data!.risk_level = 'MEDIUM';
      else data!.risk_level = 'LOW';

      setResult(data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Wallet scan failed. Try again.');
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
      link.download = `rmi-wallet-${truncate(address)}.png`;
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
    const text = [
      `RMI Wallet Scan: ${truncate(result.address)}`,
      `Risk: ${result.risk_score}/100 (${getRiskLabel(result.risk_score)})`,
      `Persona: ${getPersonaLabel(result.persona)}`,
      result.networth_usd !== undefined ? `Net Worth: ${formatUSD(result.networth_usd)}` : '',
      result.total_pnl_usd !== undefined ? `PnL: ${formatUSD(result.total_pnl_usd)}` : '',
      result.is_smart_money ? 'Smart Money: YES' : '',
      result.labels?.length ? `Labels: ${result.labels.join(', ')}` : '',
      '',
      'Scan by @rugmunchbot',
    ].filter(Boolean).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const riskColors = result ? getRiskColor(result.risk_score) : getRiskColor(0);
  const RiskIcon = riskColors.icon;
  const currentModuleData = SCAN_MODULES.find(m => m.key === currentModule) || SCAN_MODULES[0];

  return (
    <div className={`${embedded ? '' : 'min-h-screen bg-[#0a0a0f] text-slate-200 py-8'}`}>
      <div className={`${embedded ? '' : 'max-w-3xl mx-auto px-4 sm:px-6'}`}>
        {!embedded && (
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded bg-purple-950/60 border border-purple-800/40 flex items-center justify-center">
                <Wallet className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Wallet Scanner</h1>
                <p className="text-xs text-purple-400/70 font-mono tracking-wider uppercase">Full wallet forensics</p>
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
                placeholder="Enter wallet address..."
                className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-600/50"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={chain}
                onChange={e => setChain(e.target.value)}
                className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-3 text-sm text-slate-300 focus:outline-none focus:border-purple-600/50"
              >
                {chains.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
              </select>
              <button
                onClick={handleScan}
                disabled={scanning}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-sm font-bold rounded-lg transition-all flex items-center gap-2 whitespace-nowrap"
              >
                {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                {scanning ? 'Scanning...' : 'Scan'}
              </button>
            </div>
          </div>
          {error && <p className="text-xs text-red-400 mt-2 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {error}</p>}
        </div>

        {/* PROGRESS BAR */}
        {scanning && (
          <div className="bg-slate-900/60 border border-purple-500/20 rounded-xl p-4 mb-4">
            <div className="flex items-center gap-3 mb-3">
              {React.createElement(currentModuleData.icon, { className: 'w-4 h-4 text-purple-400 animate-pulse' })}
              <span className="text-sm text-purple-300">{currentModuleData.label}</span>
              <span className="ml-auto text-xs text-slate-500">{progress}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex gap-1 mt-3 overflow-hidden">
              {SCAN_MODULES.slice(0, -1).map(m => (
                <div
                  key={m.key}
                  className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                    SCAN_MODULES.findIndex(s => s.key === currentModule) >= SCAN_MODULES.findIndex(s => s.key === m.key)
                      ? 'bg-purple-500' : 'bg-slate-800'
                  }`}
                />
              ))}
            </div>
          </div>
        )}

        {/* RESULT CARD */}
        {result && (
          <div className="space-y-4">
            {/* Main Wallet Card */}
            <div ref={cardRef} className={`bg-slate-900/60 border ${riskColors.border} rounded-xl overflow-hidden`}>
              {/* Header */}
              <div className={`bg-gradient-to-r ${riskColors.gradient} p-5`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded bg-white/20 flex items-center justify-center">
                      <span className="text-white font-bold text-xs">RMI</span>
                    </div>
                    <span className="text-white/90 text-xs font-bold tracking-wider">WALLET SCAN</span>
                  </div>
                  <span className="text-white/60 text-[10px]">{new Date(result.analyzed_at).toLocaleString()}</span>
                </div>

                <div className="flex items-center gap-4">
                  <div className={`w-20 h-20 rounded-full ${riskColors.bg} border-4 ${riskColors.border} flex items-center justify-center`}>
                    <span className={`text-3xl font-bold ${riskColors.text}`}>{result.risk_score}</span>
                  </div>
                  <div>
                    <div className={`text-xl font-bold ${riskColors.text}`}>{getRiskLabel(result.risk_score)}</div>
                    <div className="text-white/70 text-xs">Risk Score / 100</div>
                    <div className="text-white/50 text-[10px] mt-0.5 font-mono">{truncate(result.address, 8, 6)}</div>
                    <div className="text-white/40 text-[10px] mt-0.5">{result.chain.toUpperCase()}</div>
                  </div>
                </div>
              </div>

              {/* Body */}
              <div className="p-5 space-y-4">
                {/* Persona */}
                <div className="flex items-center gap-3 bg-slate-800/40 rounded-lg p-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-900/40 flex items-center justify-center">
                    <Fingerprint className="w-5 h-5 text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-white">{getPersonaLabel(result.persona)}</div>
                    <div className="text-[10px] text-slate-500">Persona · {result.persona_confidence}% confidence</div>
                  </div>
                  {result.is_smart_money && (
                    <span className="px-2 py-1 bg-emerald-900/40 text-emerald-400 text-xs font-bold rounded">SMART MONEY</span>
                  )}
                </div>

                {/* Quick Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatBox icon={DollarSign} label="Net Worth" value={result.networth_usd !== undefined ? formatUSD(result.networth_usd) : 'N/A'} danger={false} />
                  <StatBox icon={result.total_pnl_usd !== undefined && result.total_pnl_usd >= 0 ? TrendingUp : TrendingDown} label="PnL" value={result.total_pnl_usd !== undefined ? formatUSD(result.total_pnl_usd) : 'N/A'} danger={result.total_pnl_usd !== undefined && result.total_pnl_usd < 0} />
                  <StatBox icon={Activity} label="TXs (recent)" value={result.tx_count_recent?.toString() || 'N/A'} danger={false} />
                  <StatBox icon={Layers} label="Tokens Held" value={result.token_count?.toString() || 'N/A'} danger={false} />
                </div>

                {/* Labels */}
                {result.labels && result.labels.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                      <Flag className="w-3.5 h-3.5 text-purple-400" /> Tags & Labels
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {result.labels.map((label, i) => (
                        <span key={i} className="px-2 py-0.5 bg-purple-950/30 text-purple-300 text-[11px] rounded-full border border-purple-800/30">
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suspicious Flags */}
                {result.suspicious_flags && result.suspicious_flags.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-400" /> Suspicious Activity ({result.suspicious_flags.length})
                    </div>
                    <div className="space-y-1.5">
                      {result.suspicious_flags.slice(0, 5).map((flag, i) => (
                        <div key={i} className={`p-2 rounded-lg text-xs ${
                          flag.severity === 'critical' ? 'bg-red-950/30 border border-red-900/30 text-red-300' :
                          flag.severity === 'high' ? 'bg-orange-950/30 border border-orange-900/30 text-orange-300' :
                          'bg-yellow-950/30 border border-yellow-900/30 text-yellow-300'
                        }`}>
                          <span className="font-bold uppercase mr-1.5">{flag.severity}</span>
                          {flag.description}
                        </div>
                      ))}
                      {result.suspicious_flags!.length > 5 && (
                        <button onClick={() => setShowDetails(!showDetails)} className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1">
                          {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          {showDetails ? 'Show less' : `+${result.suspicious_flags!.length - 5} more`}
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Sources */}
                <div className="text-[10px] text-slate-600 flex items-center gap-1.5">
                  <Zap className="w-3 h-3" />
                  Sources: {result.sources_used.join(', ') || 'basic'}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <button onClick={copyResult} className="flex-1 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-all flex items-center justify-center gap-2">
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Result'}
              </button>
              <button onClick={exportCard} disabled={generating} className="flex-1 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-all flex items-center justify-center gap-2">
                <Download className="w-3.5 h-3.5" />
                {generating ? 'Generating...' : 'Save Card'}
              </button>
              <button onClick={() => { setResult(null); setAddress(''); setProgress(0); }} className="flex-1 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-all flex items-center justify-center gap-2">
                <RefreshCw className="w-3.5 h-3.5" /> New Scan
              </button>
              {/* Cross-scan link to token scanner */}
              <button
                onClick={() => {
                  // Navigate to token scan with pre-filled address if it looks like a token CA
                  const store = (window as any).__APP_STORE__;
                  if (store) store.getState().setCurrentPage('token-scan');
                }}
                className="flex-1 py-2.5 bg-purple-900/30 border border-purple-800/40 rounded-lg text-xs font-medium text-purple-300 hover:text-white hover:bg-purple-800/40 transition-all flex items-center justify-center gap-2"
                title="Scan tokens from this wallet"
              >
                <Shield className="w-3.5 h-3.5" /> Token Scan
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── StatBox sub-component ──────────────────────────────────────────────────

function StatBox({ icon: Icon, label, value, danger }: { icon: any; label: string; value: string; danger: boolean }) {
  return (
    <div className={`bg-slate-800/40 rounded-lg p-3 text-center border ${danger ? 'border-red-900/20' : 'border-slate-700/30'}`}>
      <Icon className={`w-4 h-4 mx-auto mb-1 ${danger ? 'text-red-400' : 'text-emerald-400'}`} />
      <div className={`text-xs font-bold ${danger ? 'text-red-400' : 'text-white'}`}>{value}</div>
      <div className="text-[10px] text-slate-500">{label}</div>
    </div>
  );
}