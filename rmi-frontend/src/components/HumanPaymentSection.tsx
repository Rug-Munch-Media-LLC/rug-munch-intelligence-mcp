/**
 * HumanPaymentSection — Pay-per-call with wallet connect
 * Flow: Connect wallet → Select tool → Choose token → Pay → Execute → See result
 */
import { useState, useEffect, useCallback } from 'react';
import { useAccount, useConnect, useDisconnect, useSendTransaction } from 'wagmi';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { Wallet, Zap, CheckCircle, Loader2, ArrowRight, ExternalLink, Shield, Coins, AlertCircle } from 'lucide-react';
import { paymentService, type ToolInfo, type PaymentResult } from '../services/payments';
import { PAYMENT_TOKENS, WALLET_OPTIONS, getPhantomProvider, connectPhantom, SOLANA_PAYMENT_ADDRESS, BASE_PAYMENT_ADDRESS } from '../services/wagmi';

export default function HumanPaymentSection() {
  const { address: evmAddress, isConnected: evmConnected, chain } = useAccount();
  const { disconnect } = useDisconnect();
  const { sendTransactionAsync } = useSendTransaction();

  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [selectedTool, setSelectedTool] = useState<ToolInfo | null>(null);
  const [selectedToken, setSelectedToken] = useState('USDC-BASE');
  const [toolArgs, setToolArgs] = useState<Record<string, string>>({ address: '', chain: 'solana' });
  const [result, setResult] = useState<PaymentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState<'connect' | 'select' | 'pay' | 'result'>('connect');
  const [solAddress, setSolAddress] = useState<string | null>(null);
  const [solConnected, setSolConnected] = useState(false);

  useEffect(() => { paymentService.fetchTools().then(setTools).catch(console.error); }, []);

  const connectSolana = useCallback(async () => {
    try {
      const addr = await connectPhantom();
      setSolAddress(addr);
      setSolConnected(true);
      setStep('select');
    } catch (e: any) { setError(e.message || 'Phantom not found'); }
  }, []);

  const handlePay = async () => {
    if (!selectedTool) return;
    setLoading(true); setError('');
    try {
      const token = PAYMENT_TOKENS[selectedToken];
      const wallet = evmConnected ? evmAddress : solAddress;
      if (!wallet) throw new Error('No wallet connected');

      // EVM payment via wagmi sendTransaction
      if (token.chain !== 'Solana' && evmConnected) {
        const amountWei = BigInt(Math.floor(selectedTool.price_usdc * 10 ** token.decimals));
        const tx = await sendTransactionAsync({
          to: BASE_PAYMENT_ADDRESS as `0x${string}`,
          value: amountWei,
        });
        const res = await paymentService.executeTool(selectedTool.id, toolArgs, selectedToken, tx, wallet!);
        setResult(res); setStep('result');
      }
      // Solana payment
      else if (token.chain === 'Solana' && solConnected) {
        const provider = getPhantomProvider();
        if (!provider) throw new Error('Phantom not connected');
        const tx = await provider.signAndSendTransaction({
          recipient: SOLANA_PAYMENT_ADDRESS,
          amount: Math.floor(selectedTool.price_usdc * 1e6), // USDC decimals
        });
        const res = await paymentService.executeTool(selectedTool.id, toolArgs, selectedToken, tx.signature, wallet!);
        setResult(res); setStep('result');
      }
    } catch (e: any) { setError(e.message || 'Payment failed'); }
    finally { setLoading(false); }
  };

  const grouped = tools.reduce<Record<string, ToolInfo[]>>((acc, t) => {
    (acc[t.category] = acc[t.category] || []).push(t);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {/* Header with step indicator */}
      <div className="flex items-center gap-4 mb-4">
        {['connect', 'select', 'pay', 'result'].map((s, i) => (
          <div key={s} className={`flex items-center gap-2 text-xs ${step === s ? 'text-green-400' : 'text-gray-600'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${step === s ? 'bg-green-500/20 border border-green-500' : 'bg-gray-800 border border-gray-700'}`}>{i + 1}</div>
            <span className="capitalize hidden sm:inline">{s}</span>
            {i < 3 && <ArrowRight size={10} className="text-gray-600" />}
          </div>
        ))}
      </div>

      {/* STEP 1: Connect Wallet */}
      {step === 'connect' && (
        <div className="bg-gray-800/80 rounded-xl p-6 border border-gray-700/50">
          <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2"><Wallet size={18} className="text-green-400" /> Connect Your Wallet</h2>
          <p className="text-xs text-gray-400 mb-4">Connect to pay per call with crypto. Choose any wallet.</p>

          <div className="grid grid-cols-2 gap-3 mb-4">
            {/* EVM wallets via RainbowKit */}
            <div className="col-span-2">
              <ConnectButton.Custom>
                {({ openConnectModal, mounted }) => mounted ? (
                  <button onClick={openConnectModal} className="w-full py-3 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium text-sm hover:opacity-90 transition-opacity">
                    Connect EVM Wallet (MetaMask, WalletConnect, Coinbase)
                  </button>
                ) : null}
              </ConnectButton.Custom>
            </div>
            {/* Solana / Phantom */}
            <button onClick={connectSolana} className="py-3 rounded-lg bg-purple-900/50 border border-purple-500/30 text-purple-300 font-medium text-sm hover:bg-purple-900/80 transition-colors flex items-center justify-center gap-2">
              <span className="text-lg">👻</span> Phantom (Solana)
            </button>
          </div>

          {evmConnected && <div className="text-xs text-green-400 flex items-center gap-2"><CheckCircle size={12} /> EVM Connected: {evmAddress?.slice(0, 6)}...{evmAddress?.slice(-4)} <button onClick={() => { disconnect(); setStep('connect'); }} className="text-red-400 ml-2 hover:underline">Disconnect</button></div>}
          {solConnected && <div className="text-xs text-green-400 flex items-center gap-2"><CheckCircle size={12} /> Solana Connected: {solAddress?.slice(0, 6)}...{solAddress?.slice(-4)} <button onClick={() => { setSolConnected(false); setSolAddress(null); setStep('connect'); }} className="text-red-400 ml-2 hover:underline">Disconnect</button></div>}

          {(evmConnected || solConnected) && (
            <button onClick={() => setStep('select')} className="mt-4 w-full py-2.5 rounded-lg bg-green-600 text-white font-medium text-sm hover:bg-green-500 transition-colors">Continue to Tool Selection →</button>
          )}
          {error && <div className="mt-3 text-xs text-red-400 flex items-center gap-1"><AlertCircle size={12} /> {error}</div>}
        </div>
      )}

      {/* STEP 2: Select Tool */}
      {step === 'select' && (
        <div className="bg-gray-800/80 rounded-xl p-6 border border-gray-700/50">
          <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2"><Zap size={18} className="text-green-400" /> Choose a Tool</h2>
          <p className="text-xs text-gray-400 mb-4">Pick a tool and enter the target address or query.</p>

          {/* Tool args */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <input type="text" placeholder="Address / Token / Query" value={toolArgs.address || ''}
              onChange={e => setToolArgs({ ...toolArgs, address: e.target.value })}
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-green-500 outline-none" />
            <select value={toolArgs.chain || 'solana'} onChange={e => setToolArgs({ ...toolArgs, chain: e.target.value })}
              className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:border-green-500 outline-none">
              <option value="solana">Solana</option><option value="base">Base</option><option value="ethereum">Ethereum</option>
            </select>
          </div>

          {/* Tool grid by category */}
          <div className="max-h-64 overflow-y-auto space-y-3">
            {Object.entries(grouped).sort(([,a],[,b]) => b.length - a.length).map(([cat, catTools]) => (
              <div key={cat}>
                <div className="text-[10px] text-gray-500 uppercase mb-1">{cat} ({catTools.length})</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {catTools.slice(0, 8).map(t => (
                    <button key={t.id} onClick={() => { setSelectedTool(t); setStep('pay'); }}
                      className={`text-left p-2 rounded-lg border text-xs transition-colors ${selectedTool?.id === t.id ? 'border-green-500 bg-green-500/10' : 'border-gray-700/50 bg-gray-900/40 hover:border-green-500/30'}`}>
                      <div className="flex justify-between"><span className="text-white font-medium truncate">{t.name}</span><span className="text-green-400 font-mono ml-1 shrink-0">${t.price_usdc}</span></div>
                      <div className="text-gray-500 truncate mt-0.5">{t.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <button onClick={() => setStep('connect')} className="mt-4 text-xs text-gray-500 hover:text-gray-300">← Back</button>
        </div>
      )}

      {/* STEP 3: Pay */}
      {step === 'pay' && selectedTool && (
        <div className="bg-gray-800/80 rounded-xl p-6 border border-green-500/20">
          <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2"><Coins size={18} className="text-green-400" /> Pay & Execute</h2>
          <p className="text-xs text-gray-400 mb-4">Send payment to execute <span className="text-green-400 font-medium">{selectedTool.name}</span></p>

          <div className="bg-gray-900/60 rounded-lg p-3 mb-4 border border-gray-700/30">
            <div className="flex justify-between text-sm"><span className="text-gray-400">Tool</span><span className="text-white">{selectedTool.name}</span></div>
            <div className="flex justify-between text-sm mt-1"><span className="text-gray-400">Cost</span><span className="text-green-400 font-mono font-bold">${selectedTool.price_usdc} USDC</span></div>
            <div className="flex justify-between text-xs mt-1"><span className="text-gray-400">Target</span><span className="text-gray-300 font-mono">{toolArgs.address || '(none)'}</span></div>
          </div>

          {/* Payment method selector */}
          <div className="mb-4">
            <div className="text-xs text-gray-400 mb-2">Pay with:</div>
            <div className="grid grid-cols-5 gap-2">
              {Object.entries(PAYMENT_TOKENS).map(([key, tok]) => (
                <button key={key} onClick={() => setSelectedToken(key)}
                  className={`p-2 rounded-lg border text-xs text-center transition-colors ${selectedToken === key ? 'border-green-500 bg-green-500/10 text-green-400' : 'border-gray-700 bg-gray-900/40 text-gray-400 hover:border-green-500/30'}`}>
                  <div className="font-bold">{tok.symbol}</div>
                  <div className="text-[9px] text-gray-500">{tok.chain}</div>
                </button>
              ))}
            </div>
          </div>

          <button onClick={handlePay} disabled={loading}
            className="w-full py-3 rounded-lg bg-green-600 text-white font-bold text-sm hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2">
            {loading ? <><Loader2 size={16} className="animate-spin" /> Processing...</> : <>Pay ${selectedTool.price_usdc} → Execute</>}
          </button>

          {error && <div className="mt-3 text-xs text-red-400 flex items-center gap-1"><AlertCircle size={12} /> {error}</div>}
          <button onClick={() => setStep('select')} className="mt-3 text-xs text-gray-500 hover:text-gray-300">← Back to tool selection</button>
        </div>
      )}

      {/* STEP 4: Result */}
      {step === 'result' && result && (
        <div className="bg-gray-800/80 rounded-xl p-6 border border-green-500/20">
          <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
            {result.success ? <CheckCircle size={18} className="text-green-400" /> : <AlertCircle size={18} className="text-red-400" />}
            {result.success ? 'Execution Complete' : 'Execution Failed'}
          </h2>
          {result.txHash && <div className="text-xs text-gray-400 mt-1 flex items-center gap-1"><Shield size={10} /> TX: <span className="font-mono text-green-400">{result.txHash.slice(0, 12)}...{result.txHash.slice(-6)}</span></div>}

          <div className="bg-gray-900/60 rounded-lg p-4 mt-4 border border-gray-700/30 max-h-96 overflow-y-auto">
            <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{JSON.stringify(result.result, null, 2)}</pre>
          </div>

          <div className="flex gap-2 mt-4">
            <button onClick={() => { setResult(null); setError(''); setStep('select'); }} className="flex-1 py-2.5 rounded-lg bg-gray-700 text-white text-sm hover:bg-gray-600 transition-colors">Try Another Tool</button>
            {result.txHash && <a href={`https://basescan.org/tx/${result.txHash}`} target="_blank" rel="noopener" className="py-2.5 px-4 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-500 transition-colors flex items-center gap-1"><ExternalLink size={12} /> View TX</a>}
          </div>
        </div>
      )}
    </div>
  );
}
