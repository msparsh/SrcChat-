import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Clock, 
  Coins, 
  Cpu, 
  RefreshCw, 
  Layers,
  ArrowUpRight
} from 'lucide-react';

export const UsagePage: React.FC = () => {
  const [telemetry, setTelemetry] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchTelemetry = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/usage/telemetry');
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Telemetry & Usage Analytics</h2>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time LLM token consumption, cost estimates, and latency instrumented via <span className="font-mono text-emerald-400">llmtrack</span>.
          </p>
        </div>
        <button
          onClick={fetchTelemetry}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900 border border-zinc-800/80 p-5 rounded-2xl">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Total LLM Calls</span>
            <Cpu className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">
            {telemetry?.total_calls || 0}
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800/80 p-5 rounded-2xl">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Tokens Processed</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono">
            {telemetry?.total_tokens?.toLocaleString() || 0}
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800/80 p-5 rounded-2xl">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Estimated Cost</span>
            <Coins className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono">
            ${telemetry?.total_cost_usd?.toFixed(6) || '0.000000'}
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800/80 p-5 rounded-2xl">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Avg Latency</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono">
            {telemetry?.avg_latency_ms || 0} <span className="text-xs font-normal text-zinc-400">ms</span>
          </div>
        </div>
      </div>

      {/* Model Breakdown */}
      <div className="bg-zinc-900 border border-zinc-800/80 rounded-2xl p-6">
        <h3 className="text-sm font-semibold uppercase text-zinc-300 tracking-wider mb-4">
          Breakdown by Model
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="border-b border-zinc-800 text-zinc-400 font-mono">
              <tr>
                <th className="pb-3 font-medium">Model</th>
                <th className="pb-3 font-medium">Calls</th>
                <th className="pb-3 font-medium">Total Tokens</th>
                <th className="pb-3 font-medium">Cost (USD)</th>
                <th className="pb-3 font-medium">Avg Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60 font-mono">
              {telemetry?.by_model && Object.entries(telemetry.by_model).map(([model, stats]: [string, any]) => (
                <tr key={model} className="hover:bg-zinc-800/30">
                  <td className="py-3 text-white font-semibold">{model}</td>
                  <td className="py-3">{stats.calls}</td>
                  <td className="py-3">{stats.tokens.toLocaleString()}</td>
                  <td className="py-3 text-amber-400">${stats.cost.toFixed(6)}</td>
                  <td className="py-3">{(stats.latency_sum / (stats.calls || 1)).toFixed(1)} ms</td>
                </tr>
              ))}
              {(!telemetry?.by_model || Object.keys(telemetry.by_model).length === 0) && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-zinc-500 font-sans">
                    No telemetry records logged yet. Query repositories or use quick actions to trigger LLM calls.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Telemetry Stream */}
      <div className="bg-zinc-900 border border-zinc-800/80 rounded-2xl p-6">
        <h3 className="text-sm font-semibold uppercase text-zinc-300 tracking-wider mb-4">
          Recent LLM & Embedding Invocations
        </h3>
        <div className="space-y-2">
          {telemetry?.recent_calls?.slice().reverse().map((call: any, idx: number) => (
            <div key={idx} className="flex items-center justify-between p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/60 font-mono text-xs">
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                  call.call_type === 'llm' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                }`}>
                  {call.call_type}
                </span>
                <span className="text-white font-medium">{call.model}</span>
                {call.error && <span className="text-red-400">Error: {call.error}</span>}
              </div>
              <div className="flex items-center gap-4 text-zinc-400">
                <span>{call.total_tokens} tokens</span>
                <span>{call.latency_ms.toFixed(1)}ms</span>
                <span className="text-amber-400">${call.cost_usd.toFixed(6)}</span>
              </div>
            </div>
          ))}
          {(!telemetry?.recent_calls || telemetry.recent_calls.length === 0) && (
            <div className="text-center py-6 text-zinc-500 text-xs">No recent telemetry calls.</div>
          )}
        </div>
      </div>
    </div>
  );
};
