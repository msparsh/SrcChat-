import React from 'react';
import { 
  GitBranch, 
  RotateCw, 
  Trash2, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Cpu, 
  Layers, 
  FileText 
} from 'lucide-react';
import { Repo } from '../types';

interface Props {
  repo: Repo;
  onSync: (id: string) => void;
  onDelete: (id: string) => void;
}

export const RepoCard: React.FC<Props> = ({ repo, onSync, onDelete }) => {
  const getStatusBadge = () => {
    switch (repo.status) {
      case 'ready':
        return (
          <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Ready
          </span>
        );
      case 'failed':
        return (
          <span className="flex items-center gap-1.5 text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full font-medium">
            <AlertCircle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      case 'cloning':
      case 'parsing':
      case 'embedding':
        return (
          <span className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full font-medium animate-pulse">
            <RotateCw className="w-3 h-3 animate-spin" />
            {repo.status.charAt(0).toUpperCase() + repo.status.slice(1)} ({Math.round(repo.progress * 100)}%)
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 text-xs text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded-full font-medium">
            <Clock className="w-3.5 h-3.5" />
            Queued
          </span>
        );
    }
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800/80 rounded-xl p-4 transition-all hover:border-zinc-700">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="min-w-0">
          <h4 className="font-semibold text-sm text-white truncate" title={`${repo.owner}/${repo.name}`}>
            {repo.owner}/{repo.name}
          </h4>
          <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono mt-0.5">
            <GitBranch className="w-3 h-3" />
            <span>{repo.branch}</span>
            {repo.commit_sha && (
              <span className="text-zinc-400">({repo.commit_sha.slice(0, 7)})</span>
            )}
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {/* Progress bar if actively indexing */}
      {['cloning', 'parsing', 'embedding'].includes(repo.status) && (
        <div className="mt-3">
          <div className="w-full bg-zinc-950 rounded-full h-1.5 overflow-hidden">
            <div 
              className="bg-emerald-500 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${Math.round(repo.progress * 100)}%` }}
            />
          </div>
          <span className="text-[11px] text-zinc-400 mt-1 block truncate">
            {repo.status_message || 'Indexing repository...'}
          </span>
        </div>
      )}

      {/* Error state */}
      {repo.status === 'failed' && repo.error && (
        <div className="mt-2 text-xs text-red-400 bg-red-950/30 p-2 rounded border border-red-900/50">
          {repo.error}
        </div>
      )}

      {/* Stats summary if ready */}
      {repo.status === 'ready' && repo.size_stats && (
        <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] font-mono text-zinc-400 bg-zinc-950/60 p-2 rounded border border-zinc-800/60">
          <div className="flex items-center gap-1.5">
            <FileText className="w-3 h-3 text-zinc-400" />
            <span>{repo.size_stats.file_count || 0} files</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Layers className="w-3 h-3 text-zinc-400" />
            <span>{repo.size_stats.loc?.toLocaleString() || 0} LOC</span>
          </div>
        </div>
      )}

      {/* Action controls */}
      <div className="flex items-center justify-end gap-2 mt-3 pt-2 border-t border-zinc-800/60">
        <button
          onClick={() => onSync(repo.id)}
          title="Incremental re-index (scans changed commit SHAs & hashes)"
          className="p-1.5 text-zinc-400 hover:text-white rounded hover:bg-zinc-800 transition-colors"
        >
          <RotateCw className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => onDelete(repo.id)}
          title="Delete repository and clean up index"
          className="p-1.5 text-zinc-400 hover:text-red-400 rounded hover:bg-zinc-800 transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
