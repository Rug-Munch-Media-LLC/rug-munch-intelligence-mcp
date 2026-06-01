/**
 * Watchlist — Token & Wallet Monitoring
 * Two-tab layout with add/remove, auto-rescan, localStorage fallback
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Eye, Plus, Trash2, X, RefreshCw, Shield, AlertTriangle,
  CheckCircle2, Clock, Tag, Link2, Search
} from 'lucide-react';
import api from '../services/api';
import { useAppStore } from '../store/appStore';

// ─── Types ────────────────────────────────────────────────

interface WatchlistItem {
  address: string;
  type: 'Token' | 'Wallet';
  chain: string;
  risk_score?: number;
  tags: string[];
  added_at: string;
  last_scanned?: string;
}

type TabType = 'Tokens' | 'Wallets';

const CHAINS = ['solana', 'ethereum', 'bsc', 'base', 'arbitrum', 'polygon'];

const RISK_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  low: { bg: 'bg-emerald-950/30', text: 'text-emerald-400', border: 'border-emerald-800/40' },
  medium: { bg: 'bg-yellow-950/30', text: 'text-yellow-400', border: 'border-yellow-800/40' },
  high: { bg: 'bg-orange-950/30', text: 'text-orange-400', border: 'border-orange-800/40' },
  critical: { bg: 'bg-red-950/30', text: 'text-red-400', border: 'border-red-800/40' },
  unknown: { bg: 'bg-slate-900/40', text: 'text-slate-400', border: 'border-slate-800/40' },
};

const RISK_LABELS: Record<string, string> = {
  low: 'LOW',
  medium: 'MEDIUM',
  high: 'HIGH',
  critical: 'CRITICAL',
  unknown: 'N/A',
};

function getRiskLevel(score?: number): string {
  if (score === undefined || score === null) return 'unknown';
  if (score >= 70) return 'critical';
  if (score >= 40) return 'high';
  if (score >= 20) return 'medium';
  return 'low';
}

function truncateAddress(addr: string): string {
  if (!addr || addr.length <= 10) return addr || '';
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

// ─── Component ────────────────────────────────────────────

export default function Watchlist() {
  const user = useAppStore((s) => s.user);
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);

  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('Tokens');
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [rescanLoading, setRescanLoading] = useState(false);

  // Add form
  const [addAddress, setAddAddress] = useState('');
  const [addType, setAddType] = useState<'Token' | 'Wallet'>('Token');
  const [addChain, setAddChain] = useState('solana');
  const [addTags, setAddTags] = useState('');

  const userId = user?.id || 'local';
  const isLocal = !isAuthenticated;

  // ─── Load watchlist ────────────────────────────────────

  const loadWatchlist = useCallback(async () => {
    if (isLocal) {
      const stored = localStorage.getItem('rmi_watchlist');
      if (stored) {
        try {
          setItems(JSON.parse(stored));
        } catch {
          setItems([]);
        }
      }
      return;
    }
    setLoading(true);
    try {
      const res = await api.client.get(`/api/v1/watchlist/${userId}`);
      const data = res.data?.items || res.data || [];
      setItems(Array.isArray(data) ? data : []);
    } catch {
      // Fallback to localStorage
      const stored = localStorage.getItem('rmi_watchlist');
      if (stored) {
        try {
          setItems(JSON.parse(stored));
        } catch {
          setItems([]);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [userId, isLocal]);

  useEffect(() => {
    loadWatchlist();
  }, [loadWatchlist]);

  // ─── Persist ────────────────────────────────────────────

  const persist = useCallback(
    (updated: WatchlistItem[]) => {
      setItems(updated);
      localStorage.setItem('rmi_watchlist', JSON.stringify(updated));
    },
    []
  );

  // ─── Add item ────────────────────────────────────────────

  const handleAdd = async () => {
    if (!addAddress.trim()) {
      setError('Enter an address');
      return;
    }
    setError('');

    const newItem: WatchlistItem = {
      address: addAddress.trim(),
      type: addType,
      chain: addChain,
      tags: addTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
      added_at: new Date().toISOString(),
    };

    if (!isLocal) {
      try {
        await api.client.post('/api/v1/watchlist', {
          user_id: userId,
          address: newItem.address,
          type: newItem.type,
          chain: newItem.chain,
          tags: newItem.tags,
        });
      } catch {
        // Still add locally even if API fails
      }
    }

    persist([newItem, ...items]);
    setShowAddModal(false);
    setAddAddress('');
    setAddTags('');
  };

  // ─── Remove item ─────────────────────────────────────────

  const handleRemove = async (address: string) => {
    if (!isLocal) {
      try {
        await api.client.delete(`/api/v1/watchlist/${userId}/${address}`);
      } catch {
        // Continue removing locally
      }
    }
    persist(items.filter((i) => i.address !== address));
  };

  // ─── Auto-rescan ─────────────────────────────────────────

  const rescanAll = useCallback(async () => {
    setRescanLoading(true);
    const updated = [...items];

    for (let i = 0; i < updated.length; i++) {
      const item = updated[i];
      try {
        let data;
        if (item.type === 'Token') {
          try {
            data = await api.fullCryptoScan(item.address, item.chain);
          } catch {
            data = await api.tokenScan(item.address, item.chain);
          }
        } else {
          data = await api.walletScan(item.address, item.chain);
        }
        updated[i] = {
          ...item,
          risk_score: data.risk_score ?? data.risk,
          last_scanned: new Date().toISOString(),
        };
      } catch {
        // skip failed scans
      }
    }

    persist(updated);
    setRescanLoading(false);
  }, [items, persist]);

  // Auto rescan every 5 min
  useEffect(() => {
    const interval = setInterval(rescanAll, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [rescanAll]);

  // ─── Filtered items ──────────────────────────────────────

  const filtered = items.filter((i) =>
    activeTab === 'Tokens' ? i.type === 'Token' : i.type === 'Wallet'
  );

  // ─── Render ──────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-slate-200 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-purple-950/60 border border-purple-800/40 flex items-center justify-center">
              <Eye className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Watchlist</h1>
              <p className="text-xs text-purple-400/70 font-mono tracking-wider uppercase">
                Monitoring {items.length} item{items.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={rescanAll}
              disabled={rescanLoading}
              className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1.5 transition-colors border border-slate-700/50 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${rescanLoading ? 'animate-spin' : ''}`} />
              Rescan
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-3 py-1.5 text-xs rounded-lg bg-purple-600 hover:bg-purple-500 text-white flex items-center gap-1.5 transition-colors font-medium"
            >
              <Plus className="w-3.5 h-3.5" />
              Add to Watchlist
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-slate-900/40 border border-slate-800/40 rounded-lg p-1 w-fit">
          {(['Tokens', 'Wallets'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                activeTab === tab
                  ? 'bg-purple-600 text-white font-medium'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/40'
              }`}
            >
              {tab} ({items.filter((i) => (tab === 'Tokens' ? i.type === 'Token' : i.type === 'Wallet')).length})
            </button>
          ))}
        </div>

        {/* Items */}
        {filtered.length === 0 ? (
          <div className="bg-slate-900/30 border border-slate-800/30 rounded-xl p-8 text-center">
            <Eye className="w-12 h-12 text-purple-500/30 mx-auto mb-3" />
            <p className="text-slate-400 text-sm">No {activeTab.toLowerCase()} on your watchlist yet</p>
            <p className="text-slate-500 text-xs mt-1">Click "Add to Watchlist" to start tracking</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-4 px-4 py-2 text-sm bg-purple-600 hover:bg-purple-500 text-white rounded-lg flex items-center gap-2 mx-auto transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add your first {activeTab.toLowerCase().replace(/s$/, '')}
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((item) => {
              const level = getRiskLevel(item.risk_score);
              const colors = RISK_COLORS[level];
              return (
                <div
                  key={item.address}
                  className={`${colors.bg} border ${colors.border} rounded-xl p-3 flex items-center gap-3 group`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`${colors.text} text-xs font-bold px-2 py-0.5 rounded ${colors.bg} border ${colors.border}`}>
                        {item.risk_score !== undefined ? `${item.risk_score}/100` : 'N/A'}
                      </span>
                      <span className={`text-xs font-medium ${colors.text}`}>
                        {RISK_LABELS[level]}
                      </span>
                      <span className="text-[10px] text-slate-500 bg-slate-800/60 px-1.5 py-0.5 rounded">
                        {item.chain.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Link2 className="w-3 h-3 text-slate-500 flex-shrink-0" />
                      <span className="text-white/90 text-sm font-mono truncate">{truncateAddress(item.address)}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      {item.tags.map((tag, i) => (
                        <span
                          key={i}
                          className="text-[10px] text-slate-400 bg-slate-800/60 px-1.5 py-0.5 rounded flex items-center gap-0.5"
                        >
                          <Tag className="w-2.5 h-2.5" />
                          {tag}
                        </span>
                      ))}
                      <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                        <Clock className="w-2.5 h-2.5" />
                        {new Date(item.added_at).toLocaleDateString()}
                      </span>
                      {item.last_scanned && (
                        <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                          <RefreshCw className="w-2.5 h-2.5" />
                          Scanned {new Date(item.last_scanned).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemove(item.address);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-red-950/30 hover:bg-red-950/60 text-red-400 border border-red-900/30 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Add Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowAddModal(false)}>
            <div className="bg-slate-900 border border-slate-800/60 rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-white">Add to Watchlist</h2>
                <button onClick={() => setShowAddModal(false)} className="p-1 text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Address</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      value={addAddress}
                      onChange={(e) => setAddAddress(e.target.value)}
                      placeholder="Token or wallet address..."
                      className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-600/50"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Type</label>
                    <select
                      value={addType}
                      onChange={(e) => setAddType(e.target.value as 'Token' | 'Wallet')}
                      className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-purple-600/50"
                    >
                      <option value="Token">Token</option>
                      <option value="Wallet">Wallet</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Chain</label>
                    <select
                      value={addChain}
                      onChange={(e) => setAddChain(e.target.value)}
                      className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-purple-600/50"
                    >
                      {CHAINS.map((c) => (
                        <option key={c} value={c}>
                          {c.charAt(0).toUpperCase() + c.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Tags (comma separated)</label>
                  <input
                    type="text"
                    value={addTags}
                    onChange={(e) => setAddTags(e.target.value)}
                    placeholder="e.g. defi, rug-watch, high-value"
                    className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-purple-600/50"
                  />
                </div>

                {error && <p className="text-red-400 text-xs">{error}</p>}

                <button
                  onClick={handleAdd}
                  className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Add to Watchlist
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}