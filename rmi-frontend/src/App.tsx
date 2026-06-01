/**
 * RMI Frontend Application
 * React + Vite + TypeScript + Tailwind
 *
 * Connected Backends:
 * - Supabase (PostgreSQL) for persistent data
 * - FastAPI backend with Dragonfly caching
 */
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import WalletScanner from './components/WalletScanner';
import Wallets from './components/Wallets';
import Analytics from './components/Analytics';
import AuthPage from './components/AuthPage';
import AdminPanel from './components/AdminPanel';

import { useAppStore } from './store/appStore';
import { useEffect } from 'react';
import { supabase } from './services/supabase';

// New retail pages
import LandingPage from './components/LandingPage';

// Management & Control Panels
import AdvisorPanel from './components/AdvisorPanel';
import WalletManager from './components/WalletManager';
import SystemStatus from './components/SystemStatus';
import BotManager from './components/BotManager';
import SwarmManager from './components/SwarmManager';
import TransparencyDashboard from './components/TransparencyDashboard';
import RnDDepartment from './components/RnDDepartment';
import ComplianceDept from './components/ComplianceDept';
import SocialMediaManager from './components/SocialMediaManager';
import DAOManagement from './components/DAOManagement';
import TwitterOptimizer from './components/TwitterOptimizer';
import BackupManagement from './components/BackupManagement';
import NewsletterManager from './components/NewsletterManager';
import APIManagement from './components/APIManagement';
import RehabManager from './components/RehabManager';
import SecureWalletManager from './components/SecureWalletManager';
import FundsManager from './components/FundsManager';
import AnalyticsPanel from './components/AnalyticsPanel';
import WhitepaperManager from './components/WhitepaperManager';
import ContractDeployer from './components/ContractDeployer';
import PricingPage from './components/PricingPage';
import TrenchesPage from './components/TrenchesPage';
import RugPullRehab from './components/RugPullRehab';
import SettingsPage from './components/SettingsPage';
import ProfilePage from './components/ProfilePage';
import OnboardingModal from './components/OnboardingModal';
import EmailDashboard from './components/EmailDashboard';
// Backend admin pages — kept but not in public sidebar
import WalletClustering from './components/WalletClustering';

// New specialized departments
import WalletTools from './components/WalletTools';
import CryptoNewsPanel from './components/CryptoNewsPanel';
import CRMv2Planning from './components/CRMv2Planning';
import CapitalAcquisition from './components/CapitalAcquisition';
import CommunitySentinel from './components/CommunitySentinel';
import ProjectTreasury from './components/ProjectTreasury';
import PaymentCenter from './components/PaymentCenter';
import AirdropManager from './components/AirdropManager';
import ReferralManager from './components/ReferralManager';
import TelegramStarsManager from './components/TelegramStarsManager';
import TelegramBotManager from './components/TelegramBotManager';
import TelegramDashboard from './components/TelegramDashboard';

import GamificationProfile from './components/GamificationProfile';

// Token Intelligence Pages
import RugMapsPage from './components/RugMapsPage';
import RugChartsPage from './components/RugChartsPage';
import DataMarketPage from './components/DataMarketPage';
import DataBrokerDashboard from './components/DataBrokerDashboard';

// Intelligence & Data Pages
import TokenIntelTerminal from './components/TokenIntelTerminal';
import DailyRundown from './components/DailyRundown';
import MemeRadar from './components/MemeRadar';
import WhaleWatchers from './components/WhaleWatchers';
import PredictionIntelPage from './components/PredictionIntelPage';


// Payments & Subscriptions
import PaymentHub from './components/PaymentHub';
import RehabCheckout from './components/RehabCheckout';
import NewsletterSubscribe from './components/NewsletterSubscribe';
import TierCheckout from './components/TierCheckout';
import BulletinBoard from './components/BulletinBoard';
import TokenScanTerminal from './components/TokenScanTerminal';
import WalletScanTerminal from './components/WalletScanTerminal';
import X402Page from './components/X402Page';
import ThreatFeed from './components/ThreatFeed';
import Watchlist from './components/Watchlist';

function App() {
  const currentPage = useAppStore((state) => state.currentPage);
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const user = useAppStore((state) => state.user);
  const isAdmin = user?.role === 'ADMIN';
  const setUser = useAppStore((state) => state.setUser);
  const setAuthenticated = useAppStore((state) => state.setAuthenticated);
  const setAuthToken = useAppStore((state) => state.setAuthToken);

  // Recover OAuth/session on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setAuthToken(session.access_token);
        localStorage.setItem('access_token', session.access_token);
        setUser({
          id: session.user.id,
          email: session.user.email || '',
          role: (session.user.user_metadata?.role as any) || 'USER',
          tier: (session.user.user_metadata?.tier as any) || 'FREE',
          created_at: session.user.created_at,
        });
        setAuthenticated(true);
      }
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setAuthToken(session.access_token);
        localStorage.setItem('access_token', session.access_token);
        setUser({
          id: session.user.id,
          email: session.user.email || '',
          role: (session.user.user_metadata?.role as any) || 'USER',
          tier: (session.user.user_metadata?.tier as any) || 'FREE',
          created_at: session.user.created_at,
        });
        setAuthenticated(true);
      } else {
        setAuthToken(null);
        localStorage.removeItem('access_token');
        setUser(null);
        setAuthenticated(false);
      }
    });

    return () => { listener.subscription.unsubscribe(); };
  }, []);

  // Route to component
  // Auth wall REMOVED — all core pages accessible without login.
  // Admin panel still requires admin role. Wallet connection is optional enhancement.
  const renderPage = () => {
    // Admin-only pages
    if (currentPage === 'admin' && !isAdmin) {
      return <LandingPage />; // Non-admins see landing page, not dashboard
    }

    switch (currentPage) {
      case 'landing':
        return <LandingPage />;
      case 'dashboard':
        return <Dashboard />;
      case 'scanner':
        return <WalletScanner />;
      case 'wallets':
        return <Wallets />;
      case 'analytics':
        return <Analytics />;
      case 'rugmaps':
        return <RugMapsPage />;
      case 'rugcharts':
        return <RugChartsPage />;
      case 'datamarket':
        return <DataMarketPage />;
      case 'databroker':
        return <DataBrokerDashboard />;
      case 'clustering':
        return <WalletClustering />;
      case 'pricing':
        return <PricingPage />;
      case 'trenches':
        return <TrenchesPage />;
      case 'rehab':
        return <RugPullRehab />;
      case 'rehab-mgmt':
        return <RehabManager />;
      case 'settings':
        return <SettingsPage />;
      case 'profile':
        return <ProfilePage />;
      case 'email-dashboard':
        return <EmailDashboard />;
      case 'gamification':
        return <GamificationProfile />;

      // Intelligence & Data
      case 'intel-terminal':
        return <TokenIntelTerminal />;
      case 'prediction-intel':
        return <PredictionIntelPage />;
      case 'rundown':
        return <DailyRundown />;
      case 'meme-radar':
        return <MemeRadar />;
      case 'whale-watch':
        return <WhaleWatchers />;


      // Payments & Subscriptions
      case 'payment-hub':
        return <PaymentHub />;
      case 'rehab-checkout':
        return <RehabCheckout />;
      case 'newsletter-subscribe':
        return <NewsletterSubscribe />;
      case 'bulletin':
        return <BulletinBoard />;
      case 'tier-checkout':
        return <TierCheckout />;
      case 'token-scan':
        return <TokenScanTerminal />;
      case 'wallet-scan':
        return <WalletScanTerminal />;
      case 'threat-feed':
        return <ThreatFeed />;
      case 'watchlist':
        return <Watchlist />;
      case 'admin':
        return <AdminPanel />;

      // x402 Protocol & MCP
      case 'x402':
        return <X402Page />;

      // Management & Control Panels
      case 'advisors':
        return <AdvisorPanel />;
      case 'wallet-manager':
        return <WalletManager />;
      case 'system':
        return <SystemStatus />;
      case 'bots':
        return <BotManager />;
      case 'swarm':
        return <SwarmManager />;
      case 'transparency':
        return <TransparencyDashboard />;
      case 'rnd':
        return <RnDDepartment />;
      case 'compliance':
        return <ComplianceDept />;
      case 'social':
        return <SocialMediaManager />;
      case 'dao':
        return <DAOManagement />;
      case 'twitter-opt':
        return <TwitterOptimizer />;
      case 'backups':
        return <BackupManagement />;
      case 'newsletter':
        return <NewsletterManager />;
      case 'api-mgmt':
        return <APIManagement />;
      case 'secure-wallets':
        return <SecureWalletManager />;
      case 'funds':
        return <FundsManager />;
      case 'analytics-panel':
        return <AnalyticsPanel />;
      case 'whitepapers':
        return <WhitepaperManager />;

      // Wallet & Contract Tools
      case 'wallet-tools':
        return <WalletTools />;
      case 'contract-deployer':
        return <ContractDeployer />;

      // News & Intelligence
      case 'news-panel':
        return <CryptoNewsPanel />;

      // Planning & Strategy
      case 'crm-v2-planning':
        return <CRMv2Planning />;
      case 'capital-acquisition':
        return <CapitalAcquisition />;

      // Community & Monitoring
      case 'community-sentinel':
        return <CommunitySentinel />;

      // Treasury & Payments
      case 'project-treasury':
        return <ProjectTreasury />;
      case 'payment-center':
        return <PaymentCenter />;
      case 'airdrop-mgmt':
        return <AirdropManager />;
      case 'referrals':
        return <ReferralManager />;
      case 'telegram-stars':
        return <TelegramStarsManager />;
      case 'telegram-bots':
        return <TelegramBotManager />;
      case 'telegram-dashboard':
        return <TelegramDashboard />;


      case 'login':
        return <AuthPage />;
      default:
        return <LandingPage />;
    }
  };

  return (
    <>
      <Layout>{renderPage()}</Layout>
      <OnboardingModal />
    </>
  );
}

export default App;
