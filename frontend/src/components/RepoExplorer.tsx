import React, { useState, useEffect } from 'react';
import { FolderTree, FileCode, ChevronRight, ChevronDown, BookOpen } from 'lucide-react';
import { Repo } from '../types';

interface Props {
  repos: Repo[];
  selectedRepo: Repo | null;
  onSelectRepo: (repo: Repo) => void;
}

export const RepoExplorer: React.FC<Props> = ({ repos, selectedRepo, onSelectRepo }) => {
  const [tree, setTree] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeFile, setActiveFile] = useState<any | null>(null);

  useEffect(() => {
    if (!selectedRepo) return;
    const fetchTree = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/repos/${selectedRepo.id}/tree`);
        if (res.ok) {
          const files = await res.json();
          setTree(files);
          if (files.length > 0) setActiveFile(files[0]);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchTree();
  }, [selectedRepo]);

  if (!selectedRepo) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-zinc-500 text-sm text-center">
        <FolderTree className="w-10 h-10 mb-2 opacity-40" />
        <p>Select a repository to explore its index tree and component summaries.</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-zinc-950 border-l border-zinc-800/80">
      {/* Explorer Header */}
      <div className="p-4 border-b border-zinc-800/80">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Codebase Explorer</span>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
            {tree.length} files
          </span>
        </div>
        <select
          value={selectedRepo.id}
          onChange={(e) => {
            const found = repos.find(r => r.id === e.target.value);
            if (found) onSelectRepo(found);
          }}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-lg text-xs text-zinc-200 p-2 focus:outline-none focus:border-zinc-600"
        >
          {repos.map(r => (
            <option key={r.id} value={r.id}>
              {r.owner}/{r.name} ({r.branch})
            </option>
          ))}
        </select>
      </div>

      {/* High-level Repo Summary */}
      {selectedRepo.summary && (
        <div className="p-4 bg-zinc-900/50 border-b border-zinc-800 text-xs text-zinc-300">
          <div className="flex items-center gap-1.5 font-semibold text-emerald-400 mb-1">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Architecture Summary</span>
          </div>
          <p className="line-clamp-4 text-zinc-400 leading-relaxed">{selectedRepo.summary}</p>
        </div>
      )}

      {/* File Tree List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {loading ? (
          <div className="p-4 text-center text-zinc-500 text-xs">Loading index tree...</div>
        ) : (
          tree.map((file) => (
            <button
              key={file.id}
              onClick={() => setActiveFile(file)}
              className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-xs font-mono transition-colors ${
                activeFile?.id === file.id
                  ? 'bg-zinc-800/90 text-white font-medium'
                  : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'
              }`}
            >
              <FileCode className="w-3.5 h-3.5 flex-shrink-0 text-zinc-500" />
              <span className="truncate flex-1">{file.path}</span>
              <span className="text-[10px] text-zinc-600">{file.lines} L</span>
            </button>
          ))
        )}
      </div>

      {/* Selected File Details */}
      {activeFile && (
        <div className="p-4 border-t border-zinc-800 bg-zinc-900/70 text-xs">
          <div className="font-mono text-zinc-200 font-semibold truncate mb-1">
            {activeFile.path}
          </div>
          <div className="flex items-center gap-2 text-zinc-400 font-mono text-[11px] mb-2">
            <span>Lang: {activeFile.language}</span>
            <span>•</span>
            <span>Lines: {activeFile.lines}</span>
          </div>
          {activeFile.summary ? (
            <p className="text-zinc-300 leading-relaxed">{activeFile.summary}</p>
          ) : (
            <p className="text-zinc-500 italic">No summary generated for this unit.</p>
          )}
        </div>
      )}
    </div>
  );
};
