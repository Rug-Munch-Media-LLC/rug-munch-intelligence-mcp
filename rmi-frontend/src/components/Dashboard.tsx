import { useState, useEffect } from 'react';
import { useAppStore } from '../store/appStore';
import {
  Activity, AlertTriangle, Bell, Search, Radar,
  Map, BarChart3, Database, Share2, Users2,
  Heart, Newspaper, DollarSign, Zap
} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '';

// Types
interface PriceData { price_usd: number; change_24h: number; market_cap_usd: number }
interface TrendingToken { address: string; name: string; symbol: string; chain: string; price_usd: number; change_24h: number; volume_24h: number; liquidity_usd?: number; market_cap?: number; icon?: string }
interface RugToken { address: string; name: string; symbol: string; price_usd: number; change_24h: number; volume_24h: number }
interface Whale { wallet: string; chain: string; liquidity_usd: number; volume_24h_usd: number; token: string; dex: string }
interface BulletinPost { id: string; title: string; content: string; category: string; chain: string; upvotes: number; downvotes: number; created_at: string }
interface AlertItem { [k: string]: unknown }

// Helpers
const fmtPrice = (v: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: v < 1 ? 6 : 2 }).format(v);
const fmtPct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
const fmtNum = (v: number) => new Intl.NumberFormat('en-US', { notation: v > 1e9 ? 'compact' : 'standard', maximumFractionDigits: 2 }).format(v);
const pctCls = (v: number) => v >= 0 ? 'text-emerald-400' : 'text-red-400';

const TILES = [
  { group: 'Core', items: [
    { page: 'scanner', label: 'Wallet Scanner', Icon: Search },
    { page: 'token-scan', label: 'Token Scanner', Icon: Zap },
    { page: 'intel-terminal', label: 'Token Intel', Icon: Activity },
    { page: 'whale-watch', label: 'Whale Watch', Icon: Radar },
    { page: 'meme-radar', label: 'Meme Radar', Icon: AlertTriangle },
  ]},
  { group: 'Data', items: [
    { page: 'rugmaps', label: 'RugMaps', Icon: Map },
    { page: 'rugcharts', label: 'RugCharts', Icon: BarChart3 },
    { page: 'datamarket', label: 'Data Market', Icon: Database },
    { page: 'databroker', label: 'Data Broker', Icon: Share2 },
  ]},
  { group: 'Community', items: [
    { page: 'trenches', label: 'The Trenches', Icon: Users2 },
    { page: 'rehab', label: 'Rug Pull Rehab', Icon: Heart },
    { page: 'rundown', label: 'Daily Rundown', Icon: Newspaper },
  ]},
  { group: 'Monetize', items: [
    { page: 'payment-hub', label: 'Monetization Hub', Icon: DollarSign },
    { page: 'pricing', label: 'Pricing', Icon: DollarSign },
  ]},
];

export default function Dashboard() {
  const setCurrentPage = useAppStore((s) => s.setCurrentPage);
  const [prices, setPrices] = useState<Record<string, PriceData>>({});
  const [trending, setTrending] = useState<TrendingToken[]>([]);
  const [rugTokens, setRugTokens] = useState<RugToken[]>([]);
  const [whales, setWhales] = useState<Whale[]>([]);
  const [bulletins, setBulletins] = useState<BulletinPost[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useEffect(() => {
    const go = async (url: string) => { try { const r = await fetch(`${API}${url}`); return r.ok ? r.json() : null; } catch { return null; } };
    (async () => {
      const [mkt, trd, rug, whl, bul, alr] = await Promise.all([
        go('/api/v1/content/market-overview'),
        go('/api/v1/markets/trending'),
        go('/api/v1/rugcharts/trending?chain=solana&limit=8'),
        go('/api/v1/whales/top'),
        go('/api/v1/bulletin/latest'),
        go('/api/v1/alerts/recent'),
      ]);
      if (mkt?.prices) setPrices(mkt.prices);
      if (trd?.tokens) setTrending(trd.tokens);
      if (rug?.tokens) setRugTokens(rug.tokens);
      if (whl?.whales) setWhales(whl.whales);
      if (bul?.posts) setBulletins(bul.posts);
      if (alr?.alerts) setAlerts(alr.alerts);
    })();
  }, []);

  const coinLabel: Record<string, string> = { bitcoin: 'BTC', ethereum: 'ETH', solana: 'SOL' };

  return (
    <div className="min-h-screen bg-gray-900 p-4 grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* LEFT — Intel Feed */}
      <div className="lg:col-span-3 flex flex-col gap-4">
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h2 className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2"><Bell size={14}/> Bulletins</h2>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {bulletins.length === 0 && <p className="text-gray-500 text-xs">No bulletins</p>}
            {bulletins.slice(0, 6).map((p) => (
              <div key={p.id} className="text-xs border-l-2 border-purple-500 pl-2">
                <span className="text-white font-medium">{p.title}</span>
                <span className="text-gray-500 ml-1">({p.chain})</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h2 className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2"><AlertTriangle size={14}/> Alerts</h2>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {alerts.length === 0 && <p className="text-gray-500 text-xs">No recent alerts</p>}
            {alerts.slice(0, 5).map((a, i) => (
              <div key={i} className="text-xs text-yellow-300 border-l-2 border-yellow-500 pl-2">
                {(a as Record<string, unknown>).title as string || (a as Record<string, unknown>).message as string || 'Alert'}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h2 className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2"><Radar size={14}/> Whale Moves</h2>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {whales.length === 0 && <p className="text-gray-500 text-xs">No whale data</p>}
            {whales.slice(0, 5).map((w, i) => (
              <div key={i} className="text-xs font-mono">
                <span className="text-white">{w.wallet.slice(0, 6)}…{w.wallet.slice(-4)}</span>
                <span className="text-gray-400 ml-1">{w.token} via {w.dex}</span>
                <span className="text-emerald-400 ml-1">${fmtNum(w.volume_24h_usd)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CENTER — Market Data */}
      <div className="lg:col-span-6 flex flex-col gap-4">
        {/* Major prices */}
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(prices).map(([key, d]) => (
            <div key={key} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <div className="text-xs text-gray-400 mb-1">{coinLabel[key] || key}</div>
              <div className="text-lg font-bold text-white">{fmtPrice(d.price_usd)}</div>
              <div className={`text-xs font-medium ${pctCls(d.change_24h)}`}>{fmtPct(d.change_24h)}</div>
              <div className="text-[10px] text-gray-500 mt-1">MCap ${fmtNum(d.market_cap_usd)}</div>
            </div>
          ))}
          {Object.keys(prices).length === 0 && ['BTC', 'ETH', 'SOL'].map((s) => (
            <div key={s} className="bg-gray-800 rounded-xl p-4 border border-gray-700 animate-pulse">
              <div className="text-xs text-gray-500">{s}</div><div className="h-4 bg-gray-700 rounded mt-2 w-20" />
            </div>
          ))}
        </div>

        {/* Trending tokens */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h2 className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2"><Activity size={14}/> Trending Tokens</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left py-1">Name</th><th className="text-right">Price</th><th className="text-right">24h</th><th className="text-right">Vol</th>
              </tr></thead>
              <tbody>
                {trending.slice(0, 8).map((t) => (
                  <tr key={t.address} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="py-1.5 font-medium text-white">{t.symbol}<span className="text-gray-500 ml-1">{t.chain}</span></td>
                    <td className="text-right text-gray-300">{fmtPrice(t.price_usd)}</td>
                    <td className={`text-right font-medium ${pctCls(t.change_24h)}`}>{fmtPct(t.change_24h)}</td>
                    <td className="text-right text-gray-400">${fmtNum(t.volume_24h)}</td>
                  </tr>
                ))}
                {trending.length === 0 && <tr><td colSpan={4} className="py-4 text-center text-gray-500">Loading...</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        {/* RugCharts Solana Hot */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <h2 className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2"><BarChart3 size={14}/> Solana Hot Tokens</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {rugTokens.slice(0, 8).map((t) => (
              <div key={t.address} className="bg-gray-900/60 rounded-lg p-2">
                <div className="text-xs font-bold text-white">{t.symbol}</div>
                <div className="text-[10px] text-gray-400">{fmtPrice(t.price_usd)}</div>
                <div className={`text-[10px] font-medium ${pctCls(t.change_24h)}`}>{fmtPct(t.change_24h)}</div>
              </div>
            ))}
            {rugTokens.length === 0 && <p className="text-gray-500 text-xs col-span-4 py-4 text-center">Loading...</p>}
          </div>
        </div>
      </div>

      {/* RIGHT — Launch Tiles */}
      <div className="lg:col-span-3 flex flex-col gap-3">
        {TILES.map((g) => (
          <div key={g.group}>
            <h3 className="text-[10px] uppercase tracking-wider text-gray-500 mb-1.5 px-1">{g.group}</h3>
            <div className="grid grid-cols-2 gap-2">
              {g.items.map(({ page, label, Icon }) => (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-purple-500/50 rounded-lg p-3 flex flex-col items-center gap-1.5 transition-colors group"
                >
                  <Icon size={18} className="text-gray-400 group-hover:text-purple-400 transition-colors" />
                  <span className="text-[10px] text-gray-300 group-hover:text-white text-center leading-tight">{label}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}