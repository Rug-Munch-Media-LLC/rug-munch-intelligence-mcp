/**
 * EvmConnectButton — Replaces RainbowKit's ConnectButton.
 * Uses wagmi's injected connector (MetaMask, Coinbase, Brave, etc.)
 * No WalletConnect cloud dependency required.
 */
import { useAccount, useConnect, useDisconnect } from 'wagmi';
import { Wallet, CheckCircle, LogOut } from 'lucide-react';

interface EvmConnectButtonProps {
  showBalance?: boolean;
  chainStatus?: string;
  accountStatus?: string;
}

export default function EvmConnectButton(props?: EvmConnectButtonProps) {
  const { address, isConnected } = useAccount();
  const { connect, connectors } = useConnect();
  const { disconnect } = useDisconnect();

  if (isConnected && address) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-sm">
        <CheckCircle size={14} className="text-green-400" />
        <span className="text-green-400 font-mono text-xs">
          {address.slice(0, 6)}...{address.slice(-4)}
        </span>
        <button onClick={() => disconnect()} className="text-gray-500 hover:text-red-400 ml-1">
          <LogOut size={14} />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => {
        const injected = connectors.find(c => c.id === 'injected') || connectors[0];
        if (injected) connect({ connector: injected });
      }}
      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 text-white text-sm font-medium hover:opacity-90 transition-opacity"
    >
      <Wallet size={16} />
      Connect Wallet
    </button>
  );
}

// Also export as Custom for the ConnectButton.Custom pattern used by HumanPaymentSection
export const ConnectButton = {
  Custom: ({ children }: { children: (props: { openConnectModal: () => void; mounted: boolean }) => React.ReactNode }) => {
    const { isConnected } = useAccount();
    const { connect, connectors } = useConnect();
    const openConnectModal = () => {
      const injected = connectors.find(c => c.id === 'injected') || connectors[0];
      if (injected) connect({ connector: injected });
    };
    return <>{children({ openConnectModal, mounted: true })}</>;
  }
};
