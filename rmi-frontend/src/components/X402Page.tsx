import { useState, useEffect } from 'react';
import { useAppStore } from '../store/appStore';
import {
  DollarSign, Zap, Activity, Globe, Shield, Copy,
  Server, CheckCircle2, Terminal, Link2, User, Bot
} from 'lucide-react';
import HumanPaymentSection from './HumanPaymentSection';

const API = import.meta.env.VITE_API_URL || '';

interface DashboardData {
  earnings: { total_earnings_usdc: number; today_earnings_usdc: number; unique_payers: number; top_tools_by_revenue: { id: string; revenue: number }[]; top_tools_by_usage: { id: string; count: number }[] };
  trials: { trials_today: number; trials_all_time: number; unique_fingerprint_ids: number; unique_wallet_ids: number; trials_by_tool: Record<string, number> };
}
interface CatalogData {
  chains: Record<string, number>; total_tools: number; total_chains: number;
  tools: { id: string; name: string; description: string; price_usdc: number; category: string; chains: string[] }[];
}
interface McpHealth { status: string; tools: number; timestamp: string }

export default function X402Page() {
  const setCurrentPage = useAppStore((s) => s.setCurrentPage);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [catalog, setCatalog] = useState<CatalogData | null>(null);
  const [mcpHealth, setMcpHealth] = useState<McpHealth | null>(null);
  const [copiedField, setCopiedField] = useState('');
  const [mode, setMode] = useState<'bot' | 'human'>('bot');

  useEffect(() => {
    const go = async (url: string) => { try { const r = await fetch(`${API}${url}`); return r.ok ? r.json() : null; } catch { return null; } };
    (async () => {
      const [d, c, m] = await Promise.all([
        go('/api/v1/x402/dashboard'), go('/api/v1/x402/tools-catalog'), go('/mcp/health'),
      ]);
      if (d) setDashboard(d);
      if (c) setCatalog(c);
      if (m) setMcpHealth(m);
    })();
  }, []);

  const copyTo = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(''), 2000);
  };

  // Group tools by category
  const grouped = catalog?.tools.reduce<Record<string, typeof catalog.tools>>((acc, t) => {
    (acc[t.category] = acc[t.category] || []).push(t);
    return acc;
  }, {}) || {};

  const statCard = (label: string, value: string | number, icon: React.ReactNode, color: string) => (
    <div className="bg-gray-800/80 rounded-lg p-3 border border-gray-700/50 flex items-center gap-3">
      <div className={`p-2 rounded-md ${color}`}>{icon}</div>
      <div>
        <div className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</div>
        <div className="text-lg font-bold text-white">{value}</div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-900 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/30">
            <DollarSign size={20} className="text-green-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">x402 Protocol + MCP Server</h1>
            <p className="text-xs text-gray-400">Micropayment-powered AI tools & Model Context Protocol</p>
          </div>
        </div>
        <button onClick={() => setCurrentPage('dashboard')} className="text-xs text-gray-400 hover:text-white px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 hover:border-green-500/50 transition-colors">
          Back to Dashboard
        </button>
      </div>

      {/* Bot / Human Tab Toggle */}
      <div className="flex gap-2 bg-gray-800/50 rounded-lg p-1 w-fit">
        <button onClick={() => setMode('bot')} className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors ${mode === 'bot' ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'}`}>
          <Bot size={14} /> Bot API
        </button>
        <button onClick={() => setMode('human')} className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors ${mode === 'human' ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'}`}>
          <User size={14} /> Human Pay
        </button>
      </div>

      {mode === 'human' ? (
        <HumanPaymentSection />
      ) : (
      <>
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {statCard('Total Tools', catalog?.total_tools ?? '—', <Zap size={14} />, 'bg-green-500/10 text-green-400')}
        {statCard('Chains', catalog?.total_chains ?? '—', <Globe size={14} />, 'bg-green-500/10 text-green-400')}
        {statCard('Earnings', `$${(dashboard?.earnings.total_earnings_usdc ?? 0).toFixed(2)}`, <DollarSign size={14} />, 'bg-green-500/10 text-green-400')}
        {statCard('Trials Today', dashboard?.trials.trials_today ?? '—', <Activity size={14} />, 'bg-green-500/10 text-green-400')}
        {statCard('MCP Tools', mcpHealth?.tools ?? '—', <Server size={14} />, 'bg-blue-500/10 text-blue-400')}
        {statCard('MCP Status', mcpHealth?.status ?? '—', <CheckCircle2 size={14} />, mcpHealth?.status === 'healthy' ? 'bg-blue-500/10 text-blue-400' : 'bg-red-500/10 text-red-400')}
      </div>

      {/* 2-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

        {/* LEFT — x402 Tools Catalog */}
        <div className="lg:col-span-7 space-y-4">

          {/* Tools by Category */}
          <div className="bg-gray-800/80 rounded-xl p-4 border border-gray-700/50">
            <h2 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
              <Zap size={14} /> Tools Catalog
            </h2>
            <div className="space-y-3 max-h-[26rem] overflow-y-auto pr-1">
              {Object.entries(grouped).sort(([, a], [, b]) => b.length - a.length).map(([cat, tools]) => (
                <div key={cat}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs font-semibold text-green-400 capitalize">{cat}</span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-green-500/10 text-green-300 rounded">{tools.length}</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                    {tools.slice(0, 6).map((t) => (
                      <div key={t.id} className="bg-gray-900/60 rounded-md p-2 border border-gray-700/30 hover:border-green-500/30 transition-colors">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-white truncate">{t.name}</span>
                          <span className="text-[10px] text-green-400 font-mono ml-1">${t.price_usdc}</span>
                        </div>
                        <div className="text-[10px] text-gray-500 truncate mt-0.5">{t.description}</div>
                      </div>
                    ))}
                    {tools.length > 6 && <div className="text-[10px] text-gray-500 self-center">+{tools.length - 6} more</div>}
                  </div>
                </div>
              ))}
              {Object.keys(grouped).length === 0 && <p className="text-gray-500 text-xs text-center py-4">Loading catalog...</p>}
            </div>
          </div>

          {/* Chain Coverage */}
          <div className="bg-gray-800/80 rounded-xl p-4 border border-gray-700/50">
            <h2 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
              <Globe size={14} /> Chain Coverage
            </h2>
            <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
              {catalog?.chains && Object.entries(catalog.chains).map(([chain, count]) => (
                <div key={chain} className="bg-gray-900/60 rounded-lg p-2 text-center border border-gray-700/30">
                  <div className="text-xs font-medium text-white capitalize">{chain}</div>
                  <div className="text-[10px] text-green-400">{count} tools</div>
                </div>
              ))}
            </div>
          </div>

          {/* Payment Info */}
          <div className="bg-gray-800/80 rounded-xl p-4 border border-gray-700/50">
            <h2 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
              <Shield size={14} /> Payment Info
            </h2>
            <div className="space-y-2 text-xs text-gray-300">
              <div className="flex items-center justify-between bg-gray-900/40 rounded p-2">
                <span className="text-gray-400">Chain</span>
                <span className="font-mono text-green-400">Base (8453) USDC</span>
              </div>
              <div className="flex items-center justify-between bg-gray-900/40 rounded p-2">
                <span className="text-gray-400">PayTo</span>
                <span className="font-mono text-green-400 truncate ml-2">0x1E3AC01d...05C9</span>
              </div>
              <div className="flex items-center justify-between bg-gray-900/40 rounded p-2">
                <span className="text-gray-400">CF Workers</span>
                <span className="font-mono text-green-400 text-[10px]">x402-base · x402-sol</span>
              </div>
              <div className="flex items-center justify-between bg-gray-900/40 rounded p-2">
                <span className="text-gray-400">Trial</span>
                <span className="text-green-400">1 free/tool (fp) · 3 w/ wallet</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT — MCP Server */}
        <div className="lg:col-span-5 space-y-4">

          {/* MCP Health */}
          <div className="bg-gray-800/80 rounded-xl p-4 border border-blue-500/20">
            <h2 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
              <Server size={14} /> MCP Server
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-900/60 rounded-lg p-3 text-center border border-gray-700/30">
                <div className="text-2xl font-bold text-blue-400">{mcpHealth?.tools ?? '—'}</div>
                <div className="text-[10px] text-gray-400 mt-1">MCP Tools</div>
              </div>
              <div className="bg-gray-900/60 rounded-lg p-3 text-center border border-gray-700/30">
                <div className="text-2xl font-bold text-blue-400">{dashboard?.trials.trials_all_time ?? 0}</div>
                <div className="text-[10px] text-gray-400 mt-1">All-Time Trials</div>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 px-2 py-1.5 rounded bg-gray-900/40">
              <span className={`w-2 h-2 rounded-full ${mcpHealth?.status === 'healthy' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-xs text-gray-300">Status: <span className={mcpHealth?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}>{mcpHealth?.status || 'checking...'}</span></span>
              {mcpHealth?.timestamp && <span className="text-[10px] text-gray-500 ml-auto">{new Date(mcpHealth.timestamp).toLocaleTimeString()}</span>}
            </div>
          </div>

          {/* Connection Info */}
          <div className="bg-gray-800/80 rounded-xl p-4 border border-blue-500/20">
            <h2 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
              <Link2 size={14} /> How to Connect
            </h2>
            <div className="space-y-2">
              {[
                { label: 'SSE Endpoint', value: 'https://rugmunch.io/mcp/sse' },
                { label: 'HTTP Endpoint', value: 'https://rugmunch.io/mcp' },
                { label: 'Protocol', value: 'MCP 2025-03-26' },
                { label: 'Auth', value: 'API key (RMI_AUTH_TOKEN)' },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between bg-gray-900/40 rounded p-2 group">
                  <div>
                    <div className="text-[10px] text-gray-500 uppercase">{label}</div>
                    <div className="text-xs font-mono text-blue-300">{value}</div>
                  </div>
                  <button onClick={() => copyTo(value, label)} className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-700 transition-all">
                    <Copy size={12} className={copiedField === label ? 'text-green-400' : 'text-gray-400'} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Config Snippet */}
          <div className="bg-gray-800/80 rounded-xl p-4 border border-blue-500/20">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
                <Terminal size={14} /> MCP Client Config
              </h2>
              <button onClick={() => copyTo(`{\n  "mcpServers": {\n    "rmi": {\n      "url": "https://rugmunch.io/mcp/sse",\n      "headers": { "Authorization": "Bearer YOUR_API_KEY" }\n    }\n  }\n}`, 'config')} className="text-[10px] text-gray-400 hover:text-blue-400 px-2 py-1 rounded bg-gray-900/60 border border-gray-700/50 hover:border-blue-500/30 transition-colors flex items-center gap-1">
                <Copy size={10} /> {copiedField === 'config' ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre className="text-[11px] font-mono text-gray-300 bg-gray-900/60 rounded-lg p-3 border border-gray-700/30 overflow-x-auto leading-relaxed">
{`# Add to your MCP client config:
{
  "mcpServers": {
    "rmi": {
      "url": "https://rugmunch.io/mcp/sse",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}`}
            </pre>
          </div>

          {/* Top Tools by Usage */}
          {dashboard?.trials.trials_by_tool && Object.keys(dashboard.trials.trials_by_tool).length > 0 && (
            <div className="bg-gray-800/80 rounded-xl p-4 border border-gray-700/50">
              <h2 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
                <Activity size={14} /> Trial Usage by Tool
              </h2>
              <div className="space-y-1.5">
                {Object.entries(dashboard.trials.trials_by_tool).sort(([, a], [, b]) => b - a).slice(0, 8).map(([tool, count]) => (
                  <div key={tool} className="flex items-center justify-between text-xs bg-gray-900/40 rounded px-2 py-1.5">
                    <span className="text-gray-300 font-mono truncate">{tool}</span>
                    <span className="text-green-400 font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      </>
      )}
    </div>
  );
}