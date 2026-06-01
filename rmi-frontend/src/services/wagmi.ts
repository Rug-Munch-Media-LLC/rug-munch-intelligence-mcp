/**
 * Wagmi + RainbowKit Configuration
 * EVM wallets (MetaMask, WalletConnect, Coinbase) + Solana (Phantom)
 */
import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { mainnet, base, bsc } from 'wagmi/chains';
import { http } from 'wagmi';

const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'rmi-default-project-id';

export const config = getDefaultConfig({
  appName: 'RugMunch Intelligence',
  appDescription: 'AI-powered crypto scam detection & forensics',
  appUrl: 'https://rugmunch.io',
  appIcon: 'https://rugmunch.io/icon.png',
  projectId,
  chains: [mainnet, base, bsc],
  transports: {
    [mainnet.id]: http(),
    [base.id]: http(),
    [bsc.id]: http(),
  },
  ssr: false,
});

export { mainnet, base, bsc };

// Solana / Phantom wallet detection
export const SOLANA_PAYMENT_ADDRESS = 'Gix4P9AmwcZRGzr2hCEME5m2QAvY86dBfm8c7e7MpFzv';
export const BASE_PAYMENT_ADDRESS = '0x1E3AC01d0fdb976179790BDD02823196A92705C9';

export function getPhantomProvider() {
  if (typeof window === 'undefined') return null;
  const provider = (window as any).phantom?.solana;
  if (provider?.isPhantom) return provider;
  return null;
}

export async function connectPhantom(): Promise<string | null> {
  const provider = getPhantomProvider();
  if (!provider) throw new Error('Phantom not installed');
  const resp = await provider.connect();
  return resp.publicKey.toString();
}

export const PAYMENT_TOKENS: Record<string, { symbol: string; chain: string; address: string; decimals: number }> = {
  'USDC-SOL':  { symbol: 'USDC', chain: 'Solana', address: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', decimals: 6 },
  'USDC-BASE': { symbol: 'USDC', chain: 'Base',   address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6 },
  'SOL':       { symbol: 'SOL',  chain: 'Solana', address: 'So11111111111111111111111111111111111111112', decimals: 9 },
  'ETH':       { symbol: 'ETH',  chain: 'Ethereum', address: '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', decimals: 18 },
  'USDT':      { symbol: 'USDT', chain: 'Ethereum', address: '0xdAC17F958D2ee523a2206206994597C13D831ec7', decimals: 6 },
};

export const WALLET_OPTIONS = [
  { id: 'metamask', name: 'MetaMask', icon: '🦊', type: 'evm' },
  { id: 'walletconnect', name: 'WalletConnect', icon: '🔗', type: 'evm' },
  { id: 'coinbase', name: 'Coinbase Wallet', icon: '🔵', type: 'evm' },
  { id: 'phantom', name: 'Phantom', icon: '👻', type: 'solana' },
] as const;
