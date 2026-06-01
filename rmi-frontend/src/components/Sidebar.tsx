/**
 * Sidebar Navigation with Keyboard Support
 * Features: Up/down/enter navigation, focus management, ARIA accessibility
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import {
  LayoutDashboard,
  Search,
  Wallet,
  Settings,
  ChevronLeft,
  ChevronRight,
  Network,
  Terminal,
  CreditCard,
  MessageSquare,
  GraduationCap,
  Globe,
  Shield,
  Database,
  Eye,
  Bot,
  Newspaper,
  Brain,
  Target,
  Flame,
  ChevronDown,
  Trophy,
  Gem,
  BarChart3,
  Activity,
  DollarSign,
  Bell,
  Fingerprint,
  AlertTriangle,
  BookmarkPlus,
  Radio,
} from 'lucide-react';

interface MenuItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number | string }>;
  badge?: string;
  category: 'core' | 'community' | 'data' | 'monetize' | 'public' | 'admin';
}

// Core security & trading tools
const coreMenuItems: MenuItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, category: 'core' },
  { id: 'threat-feed', label: 'Live Threats', icon: Radio, badge: 'LIVE', category: 'core' },
  { id: 'token-scan', label: 'Token Scanner', icon: Shield, category: 'core' },
  { id: 'wallet-scan', label: 'Wallet Forensics', icon: Fingerprint, category: 'core' },
  { id: 'watchlist', label: 'Watchlist', icon: BookmarkPlus, badge: 'NEW', category: 'core' },
  { id: 'intel-terminal', label: 'Token Intel', icon: Brain, category: 'core' },
  { id: 'prediction-intel', label: 'Market Intel', icon: Target, category: 'core' },
  { id: 'whale-watch', label: 'Whale Watch', icon: Eye, category: 'core' },
  { id: 'meme-radar', label: 'Meme Radar', icon: Flame, category: 'core' },
  { id: 'wallets', label: 'My Wallets', icon: Wallet, category: 'core' },
];

// Community & learning
const communityMenuItems: MenuItem[] = [
  { id: 'trenches', label: 'The Trenches', icon: MessageSquare, category: 'community' },
  { id: 'rehab', label: 'Rug Pull Rehab', icon: GraduationCap, category: 'community' },
  { id: 'rundown', label: 'Daily Rundown', icon: Newspaper, category: 'community' },
  { id: 'gamification', label: 'Agent Profile', icon: Trophy, category: 'community' },
  { id: 'telegram-dashboard', label: 'Telegram Bot', icon: Bot, category: 'community' },
  { id: 'bulletin', label: 'Bulletin Board', icon: Bell, category: 'community' },
];

// Data & analytics
const dataMenuItems: MenuItem[] = [
  { id: 'rugmaps', label: 'RugMaps', icon: Globe, category: 'data' },
  { id: 'rugcharts', label: 'RugCharts', icon: Activity, category: 'data' },
  { id: 'datamarket', label: 'Data Market', icon: BarChart3, category: 'data' },
  { id: 'databroker', label: 'Data Broker', icon: Database, category: 'data' },
];

// Monetization (x402 + payments)
const monetizeMenuItems: MenuItem[] = [
  { id: 'x402', label: 'x402 + MCP', icon: DollarSign, badge: 'NEW', category: 'monetize' },
  { id: 'payment-hub', label: 'Monetization Hub', icon: Gem, category: 'monetize' },
  { id: 'tier-checkout', label: 'Upgrade Tier', icon: CreditCard, category: 'monetize' },
  { id: 'rehab-checkout', label: 'Book Rehab', icon: GraduationCap, category: 'monetize' },
  { id: 'newsletter-subscribe', label: 'Newsletter', icon: Newspaper, category: 'monetize' },
];

// Public-facing links
const publicMenuItems: MenuItem[] = [
  { id: 'pricing', label: 'Pricing', icon: CreditCard, category: 'public' },
  { id: 'landing', label: 'Website', icon: Globe, category: 'public' },
];

// Admin-only
const adminMenuItems: MenuItem[] = [
  { id: 'admin', label: 'Dev Console', icon: Terminal, badge: 'ADMIN', category: 'admin' },
  { id: 'darkroom', label: 'Darkroom', icon: Eye, badge: 'ADMIN', category: 'admin' },
];

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, currentPage, setCurrentPage, user } = useAppStore();
  const isAdmin = user?.role === 'ADMIN';
  
  const allMenuItems = [
    ...coreMenuItems,
    ...communityMenuItems,
    ...monetizeMenuItems,
    ...dataMenuItems,
    ...(sidebarOpen ? publicMenuItems : []),
    ...(isAdmin && sidebarOpen ? adminMenuItems : []),
  ];
  
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    community: true,
    monetize: true,
    data: true,
  });
  
  const navRef = useRef<HTMLElement>(null);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    setFocusedIndex(-1);
  }, [sidebarOpen]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (!allMenuItems.length) return;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        setFocusedIndex((prev) => {
          const next = prev < allMenuItems.length - 1 ? prev + 1 : prev;
          buttonRefs.current[next]?.focus();
          return next;
        });
        break;
      case 'ArrowUp':
        event.preventDefault();
        setFocusedIndex((prev) => {
          const next = prev > 0 ? prev - 1 : 0;
          buttonRefs.current[next]?.focus();
          return next;
        });
        break;
      case 'Enter':
        event.preventDefault();
        if (focusedIndex >= 0 && focusedIndex < allMenuItems.length) {
          setCurrentPage(allMenuItems[focusedIndex].id);
        }
        break;
      case 'Home':
        event.preventDefault();
        setFocusedIndex(0);
        buttonRefs.current[0]?.focus();
        break;
      case 'End':
        event.preventDefault();
        const lastIndex = allMenuItems.length - 1;
        setFocusedIndex(lastIndex);
        buttonRefs.current[lastIndex]?.focus();
        break;
      case 'Escape':
        if (!sidebarOpen) {
          toggleSidebar();
        }
        break;
    }
  }, [allMenuItems, focusedIndex, setCurrentPage, sidebarOpen, toggleSidebar]);

  useEffect(() => {
    if (sidebarOpen && buttonRefs.current[0]) {
      buttonRefs.current[0]?.focus();
      setFocusedIndex(0);
    }
  }, [sidebarOpen]);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const renderMenuItem = (item: MenuItem, index: number, totalBefore: number) => {
    const Icon = item.icon;
    const isActive = currentPage === item.id;
    const isFocused = focusedIndex === totalBefore + index;
    const itemIndex = totalBefore + index;

    return (
      <button
        key={item.id}
        ref={(el) => {
          buttonRefs.current[itemIndex] = el;
        }}
        onClick={() => setCurrentPage(item.id)}
        onFocus={() => setFocusedIndex(itemIndex)}
        onKeyDown={handleKeyDown}
        tabIndex={isFocused ? 0 : -1}
        aria-current={isActive ? 'page' : undefined}
        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
          isActive
            ? 'bg-purple-600/20 text-purple-300 border-l-2 border-purple-500'
            : isFocused
            ? 'bg-white/10 text-white ring-2 ring-purple-500/50'
            : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
        } ${sidebarOpen ? '' : 'justify-center'}`}
      >
        <Icon size={20} />
        {sidebarOpen && (
          <span className="text-sm font-medium flex items-center gap-2">
            {item.label}
            {item.badge && (
              <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 text-[10px] rounded">
                {item.badge}
              </span>
            )}
          </span>
        )}
      </button>
    );
  };

  const renderSection = (
    title: string,
    items: MenuItem[],
    sectionKey: string,
    startIndex: number
  ) => {
    if (!sidebarOpen) return null;
    
    const isExpanded = expandedSections[sectionKey];
    
    return (
      <div className="mt-4" key={sectionKey}>
        <button
          onClick={() => toggleSection(sectionKey)}
          className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide hover:text-gray-300 transition-colors"
        >
          <span>{title}</span>
          <ChevronDown
            size={14}
            className={`transition-transform duration-200 ${
              isExpanded ? 'rotate-180' : ''
            }`}
          />
        </button>
        {isExpanded && (
          <div className="mt-1 space-y-1">
            {items.map((item, idx) => renderMenuItem(item, idx, startIndex))}
          </div>
        )}
      </div>
    );
  };

  let itemCounter = 0;

  return (
    <aside
      ref={navRef}
      role="navigation"
      aria-label="Main navigation"
      className={`fixed left-0 top-0 h-full bg-[#12121a] border-r border-purple-500/20 z-50 transition-all duration-300 ${
        sidebarOpen ? 'w-64' : 'w-16'
      }`}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-purple-500/20">
        {sidebarOpen ? (
          <>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">RMI</span>
              </div>
              <span className="font-semibold text-white">Rug Munch</span>
            </div>
            <button
              onClick={toggleSidebar}
              className="p-1 rounded hover:bg-white/10 text-gray-400"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft size={20} />
            </button>
          </>
        ) : (
          <button
            onClick={toggleSidebar}
            className="p-1 rounded hover:bg-white/10 text-gray-400 mx-auto"
            aria-label="Expand sidebar"
          >
            <ChevronRight size={20} />
          </button>
        )}
      </div>

      {/* User Info */}
      {sidebarOpen && user && (
        <div className="px-4 py-3 border-b border-purple-500/10">
          <p className="text-sm text-gray-400">Signed in as</p>
          <p className="text-sm font-medium text-white truncate">
            {user.wallet_address
              ? `${user.wallet_address.slice(0, 6)}...${user.wallet_address.slice(-4)}`
              : user.email}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-purple-500/20 text-purple-300">
              {user.tier}
            </span>
            {user.wallet_address && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-300">
                Web3
              </span>
            )}
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="p-2 space-y-1 overflow-y-auto h-[calc(100%-12rem)]">
        {/* Core Tools */}
        <div className="space-y-1">
          {coreMenuItems.map((item, idx) => {
            const rendered = renderMenuItem(item, idx, itemCounter);
            itemCounter += 1;
            return rendered;
          })}
        </div>

        {/* Community Section */}
        {sidebarOpen && (
          <>
            {renderSection('Community', communityMenuItems, 'community', itemCounter)}
            {itemCounter += communityMenuItems.length}
          </>
        )}

        {/* Monetization Section */}
        {sidebarOpen && (
          <>
            {renderSection('Monetize', monetizeMenuItems, 'monetize', itemCounter)}
            {itemCounter += monetizeMenuItems.length}
          </>
        )}

        {/* Data & Analytics Section */}
        {sidebarOpen && (
          <>
            {renderSection('Data & Analytics', dataMenuItems, 'data', itemCounter)}
            {itemCounter += dataMenuItems.length}
          </>
        )}

        {/* Public Links */}
        {sidebarOpen && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <p className="px-3 text-xs text-gray-500 mb-2 font-semibold tracking-wide uppercase">
              Resources
            </p>
            {publicMenuItems.map((item, idx) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              const itemIdx = itemCounter + idx;
              
              return (
                <button
                  key={item.id}
                  ref={(el) => {
                    buttonRefs.current[itemIdx] = el;
                  }}
                  onClick={() => setCurrentPage(item.id)}
                  onFocus={() => setFocusedIndex(itemIdx)}
                  onKeyDown={handleKeyDown}
                  tabIndex={focusedIndex === itemIdx ? 0 : -1}
                  aria-current={isActive ? 'page' : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                    isActive
                      ? 'bg-green-600/20 text-green-300 border-l-2 border-green-500'
                      : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                  }`}
                >
                  <Icon size={20} />
                  <span className="text-sm font-medium">{item.label}</span>
                </button>
              );
            })}
            {(() => { itemCounter += publicMenuItems.length; return null; })()}
          </div>
        )}

        {/* Admin Section */}
        {isAdmin && sidebarOpen && (
          <div className="mt-4 pt-4 border-t border-red-500/20">
            <p className="px-3 text-xs text-red-400 mb-2 font-semibold tracking-wide">
              DEVELOPER
            </p>
            {adminMenuItems.map((item, idx) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              const itemIdx = itemCounter + publicMenuItems.length + idx;
              
              return (
                <button
                  key={item.id}
                  ref={(el) => {
                    buttonRefs.current[itemIdx] = el;
                  }}
                  onClick={() => setCurrentPage(item.id)}
                  onFocus={() => setFocusedIndex(itemIdx)}
                  onKeyDown={handleKeyDown}
                  tabIndex={focusedIndex === itemIdx ? 0 : -1}
                  aria-current={isActive ? 'page' : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                    isActive
                      ? 'bg-red-600/20 text-red-300 border-l-2 border-red-500'
                      : 'text-red-400/70 hover:bg-red-500/10 hover:text-red-300'
                  } ${sidebarOpen ? '' : 'justify-center'}`}
                >
                  <Icon size={20} />
                  {sidebarOpen && (
                    <span className="text-sm font-medium flex items-center gap-2">
                      {item.label}
                      <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 text-[10px] rounded">
                        {item.badge}
                      </span>
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Settings */}
        <div className="mt-4 pt-4 border-t border-gray-800">
          {renderMenuItem(
            { id: 'settings', label: 'Settings', icon: Settings, category: 'core' },
            0,
            itemCounter + publicMenuItems.length + adminMenuItems.length
          )}
        </div>
      </nav>

      {/* Bottom Section */}
      {sidebarOpen && (
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-purple-500/20">
          <div className="bg-gradient-to-r from-purple-600/10 to-blue-600/10 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-1">API Status</p>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-xs text-green-400">Operational</span>
            </div>
          </div>
          
          {/* Keyboard navigation hint */}
          <div className="mt-2 text-[10px] text-gray-500 text-center">
            ↑↓ Navigate • Enter Select
          </div>
        </div>
      )}
    </aside>
  );
}
