import { useState, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import {
  Server, Database, Globe, Activity, Shield, AlertTriangle, CheckCircle,
  XCircle, RefreshCw, Search, ExternalLink, ChevronRight, BarChart3,
  Zap, Users, Clock
} from 'lucide-react';
import { motion } from 'framer-motion';

const CHAINS = [
  { id: 'solana', name: 'Solana', icon: 'S', color: '#9945FF' },
  { id: 'base', name: 'Base', icon: 'B', color: '#0052FF' },
  { id: 'ethereum', name: 'Ethereum', icon: 'E', color: '#627EEA' },
  { id: 'bsc', name: 'BSC', icon: 'BNB', color: '#F0B90B' },
  { id: 'polygon', name: 'Polygon', icon: 'P', color: '#8247E5' },
  { id: 'arbitrum', name: 'Arbitrum', icon: 'A', color: '#28A0F0' },
];

const API_BASE = '';

export default function DataBrokerDashboard() {
  const setCurrentPage = useAppStore((s) => s.setCurrentPage);

  const [sources, setSources] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [scanChain, setScanChain] = useState('solana');
  const [scanAddr, setScanAddr] = useState('');
  const [scanResult, setScanResult] = useState<any>(null);
  const [scanning, setScanning] = useState(false);
  const [activeTab, setActiveTab] = useState('sources');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [srcRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/broker/sources`),
        fetch(`${API_BASE}/api/v1/broker/health`),
      ]);
      const srcData = await srcRes.json();
      const healthData = await healthRes.json();

      const srcList = Object.entries(srcData.sources || {}).map(([id, info]: [string, any]) => ({
        id, ...info as any,
        health: (healthData as any)?.sources?.[id] || { status: 'unknown' },
      }));
      setSources(srcList);
      setHealth(healthData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 30000);
    return () => clearInterval(iv);
  }, [fetchData]);

  const handleScan = async () => {
    if (!scanAddr.trim()) return;
    setScanning(true);
    setScanResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/broker/token/${scanChain}/${scanAddr.trim()}`);
      const data = await res.json();
      setScanResult(data);
    } catch (e) {
      setScanResult({ error: 'Scan failed' });
    } finally {
      setScanning(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-emerald-400';
      case 'configured': return 'text-blue-400';
      case 'degraded': return 'text-amber-400';
      case 'unconfigured': return 'text-slate-500';
      case 'down': return 'text-red-400';
      default: return 'text-slate-500';
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case 'configured': return <Server className="w-4 h-4 text-blue-400" />;
      case 'degraded': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'down': return <XCircle className="w-4 h-4 text-red-400" />;
      default: return <Clock className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-slate-200">
      <div className="border-b border-slate-800/60">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-violet-950/60 border border-violet-800/40 flex items-center justify-center">
              <Database className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Data Broker</h1>
              <p className="text-xs text-violet-400/70 font-mono tracking-wider uppercase">Multi-Chain Intelligence Aggregation</p>
            </div>
          </div>
          <p className="text-sm text-slate-400 max-w-xl">
            Aggregate token, wallet, and market data across 8+ sources and 6 chains.
            Cross-reference prices, risk scores, and on-chain intelligence.
          </p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
        {/* Stats */}
        {health && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-4 gap-3 mb-6">
            <div className="bg-slate-900/50 border border-slate-800/50 rounded-xl p-4">
              <div className="text-xs text-slate-500 mb-1">Total Sources</div>
              <div className="text-2xl font-bold text-white">{health.total_count}</div>
            </div>
            <div className="bg-slate-900/50 border border-slate-800/50 rounded-xl p-4">
              <div className="text-xs text-slate-500 mb-1">Configured</div>
              <div className="text-2xl font-bold text-emerald-400">{health.configured_count}</div>
            </div>
            <div className="bg-slate-900/50 border border-slate-800/50 rounded-xl p-4">
              <div className="text-xs text-slate-500 mb-1">Healthy</div>
              <div className="text-2xl font-bold text-emerald-400">{health.healthy_count}</div>
            </div>
            <div className="bg-slate-900/50 border border-slate-800/50 rounded-xl p-4">
              <div className="text-xs text-slate-500 mb-1">Overall</div>
              <div className={`text-lg font-bold ${health.overall_status === 'healthy' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {health.overall_status?.toUpperCase()}
              </div>
            </div>
          </motion.div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'sources', label: 'Data Sources', icon: Server },
            { id: 'scan', label: 'Token Lookup', icon: Search },
            { id: 'chains', label: 'Chain Coverage', icon: Globe },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id ? 'bg-violet-600 text-white' : 'bg-slate-800/40 text-slate-400 hover:text-white'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Sources */}
        {activeTab === 'sources' && (
          <div className="space-y-3">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-6 h-6 text-violet-400 animate-spin" />
              </div>
            ) : (
              sources.map((src) => (
                <motion.div key={src.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="bg-slate-900/40 border border-slate-800/50 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-center ${src.available ? '' : 'opacity-40'}`}>
                      <Database className={`w-5 h-5 ${src.available ? 'text-violet-400' : 'text-slate-600'}`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">{src.name}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full border border-slate-700/50 text-slate-400">{src.type}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full border border-slate-700/50 text-slate-400">{src.chain}</span>
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="flex items-center gap-1 text-xs">
                          {statusIcon(src.health?.status)}
                          <span className={statusColor(src.health?.status)}>{src.health?.status}</span>
                        </span>
                        {src.health?.latency_ms && <span className="text-xs text-slate-500">{src.health.latency_ms}ms</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${src.available ? 'bg-emerald-500' : 'bg-slate-600'}`} />
                    <span className="text-xs text-slate-400">{src.available ? 'Configured' : 'Not Configured'}</span>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        )}

        {/* Scan */}
        {activeTab === 'scan' && (
          <div className="space-y-4">
            <div className="bg-slate-900/40 border border-slate-800/50 rounded-xl p-5">
              <div className="flex gap-3 mb-4">
                {CHAINS.map((c) => (
                  <button key={c.id} onClick={() => setScanChain(c.id)}
                    className={`px-3 py-2 rounded-lg text-xs font-bold transition-all ${
                      scanChain === c.id ? 'bg-violet-600 text-white' : 'bg-slate-800/40 text-slate-400 hover:text-white'
                    }`}>
                    <span style={{ color: c.color }}>{c.icon}</span> {c.name}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input value={scanAddr} onChange={(e) => setScanAddr(e.target.value)}
                  placeholder="Token contract address..."
                  className="flex-1 bg-slate-800/50 border border-slate-700/50 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-violet-600/50" />
                <button onClick={handleScan} disabled={scanning || !scanAddr.trim()}
                  className="px-5 py-3 rounded-lg text-sm font-bold text-white bg-violet-600 hover:bg-violet-500 disabled:opacity-40 transition-all flex items-center gap-2">
                  {scanning ? <><RefreshCw className="w-4 h-4 animate-spin" /> Scanning...</> : <><Search className="w-4 h-4" /> Scan</>}
                </button>
              </div>
            </div>

            {scanResult && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                className="bg-slate-900/40 border border-slate-800/50 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-white">Scan Results</h3>
                  <span className="text-xs text-slate-500 font-mono">{scanResult.address}</span>
                </div>
                {scanResult.consensus && (
                  <div className="bg-violet-950/20 border border-violet-800/30 rounded-lg p-4 mb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <BarChart3 className="w-4 h-4 text-violet-400" />
                      <span className="text-xs font-bold text-violet-300">Price Consensus</span>
                    </div>
                    <div className="text-2xl font-bold text-white">${scanResult.consensus.median_price}</div>
                    <div className="text-xs text-slate-400 mt-1">{scanResult.consensus.price_sources} sources</div>
                  </div>
                )}
                <div className="space-y-3">
                  {Object.entries((scanResult as any)?.sources || {}).map(([name, data]: [string, any]) => {
                    if (data?.error) return null;
                    return (
                      <div key={name} className="bg-slate-800/40 border border-slate-700/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Zap className="w-3.5 h-3.5 text-violet-400" />
                          <span className="text-xs font-bold text-white uppercase">{name}</span>
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                          {Object.entries(data as Record<string, unknown>).map(([k, v]) => (
                            typeof v !== 'object' && (
                              <div key={k} className="text-xs">
                                <span className="text-slate-500">{k}: </span>
                                <span className="text-slate-300">{String(v).slice(0, 30)}</span>
                              </div>
                            )
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* Chains */}
        {activeTab === 'chains' && (
          <div className="grid grid-cols-2 gap-4">
            {CHAINS.map((c) => (
              <motion.div key={c.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="bg-slate-900/40 border border-slate-800/50 rounded-xl p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold"
                    style={{ backgroundColor: c.color + '20', color: c.color, border: `1px solid ${c.color}40` }}>
                    {c.icon}
                  </div>
                  <div>
                    <div className="text-sm font-bold text-white">{c.name}</div>
                    <div className="text-[10px] text-slate-500 uppercase">{c.id}</div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Sources Active</span>
                    <span className="text-slate-300">{sources.filter((s) => s.chain === c.id || s.chain === 'multi').length}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">API Endpoint</span>
                    <span className="text-slate-300">/broker/token/{c.id}/&lt;addr&gt;</span>
                  </div>
                  <button onClick={() => { setScanChain(c.id); setActiveTab('scan'); }}
                    className="w-full mt-2 py-2 rounded-lg text-xs font-bold text-white border border-slate-700/50 hover:border-violet-500/50 hover:bg-violet-950/20 transition-all flex items-center justify-center gap-2">
                    Scan on {c.name} <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
