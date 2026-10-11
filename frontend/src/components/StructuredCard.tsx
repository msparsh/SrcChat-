import React from 'react';
import { 
  GitBranch, 
  AlertTriangle, 
  ShieldCheck, 
  Layers, 
  Compass, 
  SplitSquareVertical, 
  ArrowRight,
  ChevronRight
} from 'lucide-react';

interface Props {
  data: any;
  mode: string;
}

export const StructuredCard: React.FC<Props> = ({ data, mode }) => {
  if (!data) return null;

  switch (mode) {
    case 'flow':
      return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 my-4 shadow-xl">
          <div className="flex items-center gap-2 mb-3 text-emerald-400 font-medium">
            <GitBranch className="w-5 h-5" />
            <span>End-to-End Flow: {data.flow_name || 'Execution Trace'}</span>
          </div>
          <p className="text-zinc-300 text-sm mb-4 leading-relaxed">{data.overview}</p>
          
          <div className="space-y-3">
            {data.steps?.map((step: any, idx: number) => (
              <div key={idx} className="flex gap-3 bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/80">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 font-mono text-xs flex items-center justify-center font-semibold">
                  {step.step_number || idx + 1}
                </span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 font-mono text-xs text-zinc-400">
                    <span className="text-zinc-200 font-semibold">{step.file_path}</span>
                    {step.symbol_or_endpoint && (
                      <span className="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded">
                        {step.symbol_or_endpoint}
                      </span>
                    )}
                  </div>
                  <p className="text-zinc-300 text-xs mt-1 leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>

          {data.caveats && (
            <div className="mt-4 text-xs text-zinc-400 bg-zinc-950 p-2.5 rounded border border-zinc-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span>{data.caveats}</span>
            </div>
          )}
        </div>
      );

    case 'impact':
      return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 my-4 shadow-xl">
          <div className="flex items-center gap-2 mb-3 text-amber-400 font-medium">
            <AlertTriangle className="w-5 h-5" />
            <span>Impact Analysis: {data.target || 'Target Component'}</span>
          </div>

          <div className="mb-4">
            <h4 className="text-xs font-semibold uppercase text-zinc-400 tracking-wider mb-2">Suggested Change Order</h4>
            <div className="flex flex-wrap items-center gap-2">
              {data.suggested_change_order?.map((item: string, i: number) => (
                <React.Fragment key={i}>
                  <span className="bg-zinc-800 text-zinc-200 font-mono text-xs px-2.5 py-1 rounded">
                    {item}
                  </span>
                  {i < data.suggested_change_order.length - 1 && (
                    <ChevronRight className="w-4 h-4 text-zinc-600" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          <div className="space-y-2.5">
            <h4 className="text-xs font-semibold uppercase text-zinc-400 tracking-wider mb-2">Risk-Ranked Impacted Units</h4>
            {data.impacted_items?.map((item: any, idx: number) => {
              const riskColor = 
                item.risk_level?.toLowerCase() === 'high' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                item.risk_level?.toLowerCase() === 'medium' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                'bg-blue-500/20 text-blue-400 border-blue-500/30';
              return (
                <div key={idx} className="bg-zinc-950/70 p-3 rounded-lg border border-zinc-800 flex items-start justify-between gap-4">
                  <div>
                    <div className="font-mono text-xs text-zinc-200 font-medium">
                      {item.file_path} {item.symbol ? `→ ${item.symbol}` : ''}
                    </div>
                    <div className="text-xs text-zinc-400 mt-1">{item.rationale}</div>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded font-mono border ${riskColor} uppercase text-[10px]`}>
                    {item.risk_level || 'MED'}
                  </span>
                </div>
              );
            })}
          </div>

          {data.static_analysis_caveat && (
            <p className="mt-4 text-xs text-zinc-400 italic">
              Note: {data.static_analysis_caveat}
            </p>
          )}
        </div>
      );

    case 'architecture':
      return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 my-4 shadow-xl">
          <div className="flex items-center gap-2 mb-3 text-indigo-400 font-medium">
            <Layers className="w-5 h-5" />
            <span>Architecture Overview</span>
          </div>
          <p className="text-zinc-300 text-sm mb-4">{data.system_overview}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <div className="bg-zinc-950/60 p-3 rounded border border-zinc-800">
              <span className="text-xs uppercase text-zinc-400 font-semibold tracking-wider">Entry Points</span>
              <ul className="mt-2 space-y-1 font-mono text-xs text-zinc-300">
                {data.entry_points?.map((ep: string, i: number) => (
                  <li key={i}>• {ep}</li>
                ))}
              </ul>
            </div>
            <div className="bg-zinc-950/60 p-3 rounded border border-zinc-800">
              <span className="text-xs uppercase text-zinc-400 font-semibold tracking-wider">Data Stores & Integrations</span>
              <ul className="mt-2 space-y-1 font-mono text-xs text-zinc-300">
                {data.data_stores?.map((ds: string, i: number) => (
                  <li key={i}>• {ds}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-xs uppercase text-zinc-400 font-semibold tracking-wider">Core Components</span>
            {data.components?.map((c: any, i: number) => (
              <div key={i} className="bg-zinc-950/80 p-3 rounded border border-zinc-800/80">
                <span className="font-semibold text-zinc-200 text-sm">{c.name}</span>
                <p className="text-xs text-zinc-400 mt-1">{c.responsibilities}</p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {c.key_files?.map((kf: string, ki: number) => (
                    <span key={ki} className="text-[10px] font-mono bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded">
                      {kf}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      );

    case 'onboarding':
      return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 my-4 shadow-xl">
          <div className="flex items-center gap-2 mb-3 text-cyan-400 font-medium">
            <Compass className="w-5 h-5" />
            <span>New Joiner Walkthrough</span>
          </div>
          <p className="text-zinc-300 text-sm mb-4">{data.summary}</p>
          
          <div className="space-y-3">
            <span className="text-xs uppercase text-zinc-400 font-semibold tracking-wider">Where to Start Reading</span>
            {data.where_to_start?.map((item: any, i: number) => (
              <div key={i} className="flex gap-3 bg-zinc-950/60 p-3 rounded-lg border border-zinc-800">
                <span className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 font-mono text-xs flex items-center justify-center font-bold">
                  {item.order || i + 1}
                </span>
                <div>
                  <div className="font-mono text-xs text-zinc-200 font-semibold">{item.file_path}</div>
                  <p className="text-xs text-zinc-400 mt-1">{item.why_read}</p>
                </div>
              </div>
            ))}
          </div>

          {data.development_workflow_notes && (
            <div className="mt-4 bg-zinc-950 p-3 rounded border border-zinc-800 text-xs text-zinc-300">
              <span className="font-semibold text-cyan-400">Workflow Note: </span>
              {data.development_workflow_notes}
            </div>
          )}
        </div>
      );

    case 'compare':
      return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 my-4 shadow-xl">
          <div className="flex items-center gap-2 mb-3 text-purple-400 font-medium">
            <SplitSquareVertical className="w-5 h-5" />
            <span>Cross-Repository Comparison</span>
          </div>
          <p className="text-zinc-300 text-sm mb-4">{data.summary}</p>

          <div className="space-y-3">
            {data.aspects?.map((aspect: any, idx: number) => (
              <div key={idx} className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800">
                <div className="font-semibold text-zinc-200 text-sm mb-2">{aspect.topic}</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-2">
                  <div className="bg-zinc-900/80 p-2.5 rounded border border-zinc-800/80">
                    <span className="text-xs text-purple-300 font-mono block font-semibold mb-1">{data.repo_a}</span>
                    <span className="text-xs text-zinc-300">{aspect.repo_a_approach}</span>
                  </div>
                  <div className="bg-zinc-900/80 p-2.5 rounded border border-zinc-800/80">
                    <span className="text-xs text-pink-300 font-mono block font-semibold mb-1">{data.repo_b}</span>
                    <span className="text-xs text-zinc-300">{aspect.repo_b_approach}</span>
                  </div>
                </div>
                <div className="text-xs text-zinc-400 bg-zinc-900/40 p-2 rounded">
                  <span className="font-semibold text-zinc-300">Tradeoffs: </span>{aspect.tradeoffs}
                </div>
              </div>
            ))}
          </div>
        </div>
      );

    default:
      return (
        <pre className="bg-zinc-900 text-zinc-300 p-4 rounded-lg font-mono text-xs overflow-x-auto border border-zinc-800">
          {JSON.stringify(data, null, 2)}
        </pre>
      );
  }
};
