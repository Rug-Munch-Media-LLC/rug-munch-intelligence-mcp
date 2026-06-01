/**
 * Payment Service — Human payment flow
 * Wallet connect → Select tool → Choose token → Sign tx → Execute → Display result
 */
import { supabase } from './supabase';

const API = import.meta.env.VITE_API_URL || '';

export interface ToolInfo {
  id: string; name: string; description: string;
  price_usdc: number; category: string; chains: string[];
}
export interface PaymentResult {
  success: boolean;
  tool: string;
  result?: any;
  error?: string;
  txHash?: string;
}

async function fetchTools(): Promise<ToolInfo[]> {
  const r = await fetch(`${API}/api/v1/x402/tools-catalog`);
  if (!r.ok) throw new Error('Failed to load tools');
  const data = await r.json();
  return data.tools || [];
}

async function executeTool(toolId: string, args: Record<string, string>, paymentToken: string, txHash: string, walletAddress: string): Promise<PaymentResult> {
  const r = await fetch(`${API}/api/v1/x402/human-execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool: toolId, arguments: args, payment_token: paymentToken, tx_hash: txHash, wallet: walletAddress }),
  });
  const data = await r.json();
  
  // Record payment in Supabase
  await supabase.from('payments').insert([{
    tool: toolId,
    amount: data.cost || 0,
    token: paymentToken,
    tx_hash: txHash,
    wallet: walletAddress,
    status: data.success ? 'completed' : 'failed',
    created_at: new Date().toISOString(),
  }]);
  
  return { success: data.success || r.ok, tool: toolId, result: data, txHash };
}

async function recordTrial(toolId: string, fingerprint: string) {
  await supabase.from('payment_trials').insert([{
    tool: toolId,
    fingerprint,
    created_at: new Date().toISOString(),
  }]);
}

export const paymentService = { fetchTools, executeTool, recordTrial };
