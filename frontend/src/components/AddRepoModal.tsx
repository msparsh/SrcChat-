import React, { useState } from 'react';
import { Plus, X, AlertCircle, Shield, CheckCircle2 } from 'lucide-react';
import { SystemLimits } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (url: string, branch: string) => Promise<void>;
  limits: SystemLimits | null;
}

export const AddRepoModal: React.FC<Props> = ({ isOpen, onClose, onSubmit, limits }) => {
  const [url, setUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const validateLive = (val: string) => {
    setUrl(val);
    setError(null);
    if (!val) return;
    if (!val.startsWith('https://github.com/')) {
      setError('Only public GitHub repositories (https://github.com/owner/repo) are supported.');
      return;
    }
    const parts = val.replace('https://github.com/', '').split('/');
    if (parts.length < 2 || !parts[0] || !parts[1]) {
      setError('Please provide both the repository owner and name.');
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.startsWith('https://github.com/')) {
      setError('Only public GitHub repositories are permitted.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onSubmit(url, branch);
      setUrl('');
      setBranch('main');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to add repository.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
        <button 
          onClick={onClose}
          className="absolute top-5 right-5 text-zinc-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-xl font-semibold text-white mb-1">Index Public GitHub Repository</h3>
        <p className="text-zinc-400 text-sm mb-5">
          SrcChat indexes code as pure text and extracts static AST call structures safely.
        </p>

        <form onSubmit={handleFormSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Repository URL</label>
            <input 
              type="text" 
              required
              value={url}
              onChange={(e) => validateLive(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Branch / Ref</label>
            <input 
              type="text" 
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-2.5 text-red-400 text-xs leading-relaxed">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Limits box */}
          <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800/80 text-xs space-y-1.5 text-zinc-400">
            <div className="flex items-center gap-1.5 text-zinc-200 font-semibold mb-1">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Enforced Public Safety Limits</span>
            </div>
            <div className="flex justify-between">
              <span>Max Repo Size:</span>
              <span className="font-mono text-zinc-300">{limits?.max_repo_size_mb || 100} MB</span>
            </div>
            <div className="flex justify-between">
              <span>Max Files:</span>
              <span className="font-mono text-zinc-300">{limits?.max_repo_files || 3000} files</span>
            </div>
            <div className="flex justify-between">
              <span>Max Lines of Code:</span>
              <span className="font-mono text-zinc-300">{limits?.max_indexed_loc?.toLocaleString() || '200,000'} LOC</span>
            </div>
            <div className="flex justify-between">
              <span>Per-File Size Cap:</span>
              <span className="font-mono text-zinc-300">{limits?.max_file_size_kb || 300} KB</span>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !!error || !url}
              className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-black font-semibold rounded-xl text-sm transition-colors flex items-center gap-2"
            >
              {loading ? 'Queuing Ingest...' : 'Add & Index Repo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
