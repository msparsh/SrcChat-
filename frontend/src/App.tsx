import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  Plus, 
  GitBranch, 
  BarChart3, 
  Layers, 
  ChevronRight, 
  ChevronDown, 
  Code2, 
  Copy, 
  Check, 
  Compass, 
  AlertTriangle, 
  SplitSquareVertical, 
  FileSearch,
  BookOpen,
  PanelRightClose,
  PanelRightOpen,
  FolderGit2
} from 'lucide-react';

import { Repo, Workspace, ChatMessage, SystemLimits, AgentStep } from './types';
import { AddRepoModal } from './components/AddRepoModal';
import { RepoCard } from './components/RepoCard';
import { StructuredCard } from './components/StructuredCard';
import { UsagePage } from './components/UsagePage';
import { RepoExplorer } from './components/RepoExplorer';

export default function App() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepoScope, setSelectedRepoScope] = useState<string[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [limits, setLimits] = useState<SystemLimits | null>(null);
  
  // View states
  const [activeTab, setActiveTab] = useState<'chat' | 'usage'>('chat');
  const [showExplorer, setShowExplorer] = useState(true);
  const [explorerRepo, setExplorerRepo] = useState<Repo | null>(null);

  // Chat states
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [openSteps, setOpenSteps] = useState<{ [msgId: string]: boolean }>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initial loads
  useEffect(() => {
    fetchLimits();
    fetchWorkspaces();
  }, []);

  useEffect(() => {
    if (currentWorkspace) {
      fetchRepos(currentWorkspace.id);
    }
  }, [currentWorkspace]);

  // Periodic polling for indexing repo status
  useEffect(() => {
    if (!currentWorkspace) return;
    const interval = setInterval(() => {
      const isIndexing = repos.some(r => ['queued', 'cloning', 'parsing', 'embedding'].includes(r.status));
      if (isIndexing) {
        fetchRepos(currentWorkspace.id);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [repos, currentWorkspace]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchLimits = async () => {
    try {
      const res = await fetch('/api/v1/info/limits');
      if (res.ok) setLimits(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchWorkspaces = async () => {
    try {
      const res = await fetch('/api/v1/workspaces');
      if (res.ok) {
        const data = await res.json();
        setWorkspaces(data);
        if (data.length > 0 && !currentWorkspace) {
          setCurrentWorkspace(data[0]);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchRepos = async (workspaceId: string) => {
    try {
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/repos`);
      if (res.ok) {
        const data: Repo[] = await res.json();
        setRepos(data);
        if (data.length > 0 && !explorerRepo) {
          setExplorerRepo(data[0]);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddRepo = async (url: string, branch: string) => {
    if (!currentWorkspace) return;
    const res = await fetch('/api/v1/repos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace_id: currentWorkspace.id,
        url,
        branch
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to add repository.');
    }
    fetchRepos(currentWorkspace.id);
  };

  const handleSyncRepo = async (repoId: string) => {
    await fetch(`/api/v1/repos/${repoId}/sync`, { method: 'POST' });
    if (currentWorkspace) fetchRepos(currentWorkspace.id);
  };

  const handleDeleteRepo = async (repoId: string) => {
    await fetch(`/api/v1/repos/${repoId}`, { method: 'DELETE' });
    if (currentWorkspace) fetchRepos(currentWorkspace.id);
  };

  const toggleRepoScope = (name: string) => {
    setSelectedRepoScope(prev => 
      prev.includes(name) ? prev.filter(r => r !== name) : [...prev, name]
    );
  };

  const handleSendMessage = async (queryText?: string, mode?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || !currentWorkspace || isStreaming) return;

    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    const newMessages: ChatMessage[] = [
      ...messages,
      { id: userMsgId, role: 'user', content: textToSend }
    ];

    setMessages([
      ...newMessages,
      { id: assistantMsgId, role: 'assistant', content: '', steps: [], mode }
    ]);
    setInputQuery('');
    setIsStreaming(true);

    try {
      // If structured quick action
      if (mode && ['flow', 'impact', 'architecture', 'onboarding', 'compare', 'legacy'].includes(mode)) {
        const res = await fetch('/api/v1/actions/structured', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mode,
            query: textToSend,
            repos: selectedRepoScope.length > 0 ? selectedRepoScope : repos.map(r => r.name)
          })
        });
        const data = await res.json();
        setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, structuredData: data, content: `Structured ${mode} analysis generated.` } : m));
        setIsStreaming(false);
        return;
      }

      // Free chat SSE streaming
      const res = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: currentWorkspace.id,
          query: textToSend,
          repos: selectedRepoScope.length > 0 ? selectedRepoScope : repos.map(r => r.name),
          output_mode: mode
        })
      });

      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let streamBuffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        streamBuffer += decoder.decode(value, { stream: true });
        const lines = streamBuffer.split('\n\n');
        streamBuffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = JSON.parse(line.replace('data: ', ''));

            if (payload.type === 'step') {
              setMessages(prev => prev.map(m => {
                if (m.id === assistantMsgId) {
                  const existingSteps = m.steps || [];
                  const existingIdx = existingSteps.findIndex(s => s.action === payload.action);
                  let updated: AgentStep[];
                  if (existingIdx >= 0) {
                    updated = [...existingSteps];
                    updated[existingIdx] = payload as AgentStep;
                  } else {
                    updated = [...existingSteps, payload as AgentStep];
                  }
                  return { ...m, steps: updated };
                }
                return m;
              }));
            } else if (payload.type === 'content_chunk') {
              setMessages(prev => prev.map(m => {
                if (m.id === assistantMsgId) {
                  return { ...m, content: m.content + payload.delta };
                }
                return m;
              }));
            } else if (payload.type === 'done') {
              setMessages(prev => prev.map(m => {
                if (m.id === assistantMsgId) {
                  return { ...m, content: payload.full_content };
                }
                return m;
              }));
            } else if (payload.type === 'error') {
              setMessages(prev => prev.map(m => {
                if (m.id === assistantMsgId) {
                  return { ...m, content: `Error: ${payload.error || 'Agent stream encountered an error.'}` };
                }
                return m;
              }));
            }
          }
        }
      }
    } catch (e) {
      console.error(e);
      setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content: 'Error streaming agent response.' } : m));
    } finally {
      setIsStreaming(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const quickActions = [
    { label: 'Explain Flow', mode: 'flow', icon: GitBranch, prompt: 'Trace the end-to-end request flow of this codebase.' },
    { label: 'Impact Analysis', mode: 'impact', icon: AlertTriangle, prompt: 'Perform an impact analysis for modifying core database models or API routes.' },
    { label: 'Architecture', mode: 'architecture', icon: Layers, prompt: 'Generate an architecture overview identifying components, entry points, and storage.' },
    { label: 'Onboarding Guide', mode: 'onboarding', icon: Compass, prompt: 'Provide a new-joiner onboarding guide with reading order and key concepts.' },
    { label: 'Compare Repos', mode: 'compare', icon: SplitSquareVertical, prompt: 'Compare architectural design and conventions between the selected repositories.' },
  ];

  return (
    <div className="flex h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* LEFT SIDEBAR */}
      <aside className="w-80 flex-shrink-0 bg-zinc-900/60 border-r border-zinc-800/80 flex flex-col justify-between">
        <div className="p-4 flex flex-col h-full overflow-hidden">
          {/* Logo / Header */}
          <div className="flex items-center justify-between pb-4 border-b border-zinc-800/80">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Bot className="w-4 h-4" />
              </div>
              <span className="font-bold text-white tracking-tight">SrcChat</span>
            </div>
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1 bg-emerald-500 hover:bg-emerald-600 text-black px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Repo</span>
            </button>
          </div>

          {/* Repositories section */}
          <div className="flex-1 overflow-y-auto py-4 space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold uppercase text-zinc-400 tracking-wider px-1">
              <span>Indexed Repos ({repos.length})</span>
              <span className="text-[10px] text-zinc-400 font-mono">Max 10</span>
            </div>

            {repos.length === 0 ? (
              <div className="text-center py-8 px-4 bg-zinc-950/40 rounded-xl border border-zinc-800/40 text-xs text-zinc-400">
                <FolderGit2 className="w-8 h-8 mx-auto mb-2 opacity-30 text-emerald-400" />
                <p>No public repos indexed yet.</p>
                <p className="mt-1 text-[11px] text-zinc-400">Add a GitHub URL to start investigating.</p>
              </div>
            ) : (
              repos.map(r => (
                <RepoCard 
                  key={r.id} 
                  repo={r} 
                  onSync={handleSyncRepo} 
                  onDelete={handleDeleteRepo} 
                />
              ))
            )}
          </div>

          {/* Navigation items */}
          <div className="pt-3 border-t border-zinc-800/80 space-y-1">
            <button
              onClick={() => setActiveTab('chat')}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                activeTab === 'chat' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
              }`}
            >
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>Agentic Chat & Quick Actions</span>
            </button>
            <button
              onClick={() => setActiveTab('usage')}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                activeTab === 'usage' ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
              }`}
            >
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <span>llmtrack Telemetry & Usage</span>
            </button>
          </div>
        </div>
      </aside>

      {/* CENTER VIEW */}
      <main className="flex-1 flex flex-col min-w-0 bg-zinc-950">
        {activeTab === 'usage' ? (
          <UsagePage />
        ) : (
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* Top Toolbar: Repo Scope Selector */}
            <header className="p-3.5 border-b border-zinc-800/80 flex items-center justify-between bg-zinc-950/80 backdrop-blur">
              <div className="flex items-center gap-2 overflow-x-auto py-0.5">
                <span className="text-xs text-zinc-400 font-medium whitespace-nowrap mr-1">Search Scope:</span>
                <button
                  onClick={() => setSelectedRepoScope([])}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors whitespace-nowrap ${
                    selectedRepoScope.length === 0
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 font-medium'
                      : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  All Repos ({repos.length})
                </button>
                {repos.map(r => {
                  const isSelected = selectedRepoScope.includes(r.name);
                  return (
                    <button
                      key={r.id}
                      onClick={() => toggleRepoScope(r.name)}
                      className={`text-xs px-2.5 py-1 rounded-full border transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                        isSelected
                          ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 font-medium'
                          : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                      <span>{r.name}</span>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => setShowExplorer(!showExplorer)}
                title="Toggle Codebase Explorer"
                className="p-1.5 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-900 transition-colors ml-3"
              >
                {showExplorer ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
              </button>
            </header>

            {/* Chat Messages Timeline */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.length === 0 ? (
                <div className="max-w-xl mx-auto my-auto text-center py-16 space-y-4">
                  <div className="w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl mx-auto flex items-center justify-center text-emerald-400">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <h3 className="text-xl font-bold text-white tracking-tight">Investigate Indexed Codebases</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed">
                    Ask questions across files and repositories. SrcChat traverses AST symbols, static call edges, and pgvector embeddings to synthesize architectural insights.
                  </p>

                  {/* Quick Action Chips */}
                  <div className="pt-4 flex flex-wrap justify-center gap-2">
                    {quickActions.map(action => {
                      const Icon = action.icon;
                      return (
                        <button
                          key={action.mode}
                          onClick={() => handleSendMessage(action.prompt, action.mode)}
                          className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-xl text-xs text-zinc-300 transition-colors"
                        >
                          <Icon className="w-3.5 h-3.5 text-emerald-400" />
                          <span>{action.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : (
                messages.map(msg => (
                  <div key={msg.id} className="max-w-3xl mx-auto space-y-3">
                    {/* User message */}
                    {msg.role === 'user' ? (
                      <div className="flex justify-end">
                        <div className="bg-zinc-800 text-zinc-100 px-4 py-2.5 rounded-2xl text-sm leading-relaxed max-w-[85%] font-medium">
                          {msg.content}
                        </div>
                      </div>
                    ) : (
                      /* Assistant response */
                      <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-5 shadow-sm space-y-3">
                        {/* Agent step timeline collapsible */}
                        {msg.steps && msg.steps.length > 0 && (
                          <div className="border-b border-zinc-800/80 pb-3">
                            <button
                              onClick={() => setOpenSteps(prev => ({ ...prev, [msg.id]: !prev[msg.id] }))}
                              className="flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
                            >
                              {openSteps[msg.id] ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                              <span>Agent Execution Steps ({msg.steps.length} tools executed)</span>
                            </button>
                            {openSteps[msg.id] && (
                              <div className="mt-2 space-y-1.5 pl-4 border-l-2 border-emerald-500/30 font-mono text-xs text-zinc-400">
                                {msg.steps.map((step, idx) => (
                                  <div key={idx} className="flex items-center gap-2">
                                    <span className="text-emerald-400">[{step.action}]</span>
                                    <span>{step.status}</span>
                                    {step.result_count !== undefined && <span className="text-zinc-400">({step.result_count} hits)</span>}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Structured Output Card if available */}
                        {msg.structuredData && (
                          <StructuredCard data={msg.structuredData} mode={msg.mode || ''} />
                        )}

                        {/* Synthesized Markdown / Text */}
                        <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
                          {msg.content || (isStreaming ? <span className="animate-pulse text-zinc-400">Synthesizing codebase analysis...</span> : '')}
                        </div>

                        {/* Copy button */}
                        <div className="flex justify-end pt-2">
                          <button
                            onClick={() => copyToClipboard(msg.content, msg.id)}
                            className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
                          >
                            {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>{copiedId === msg.id ? 'Copied' : 'Copy'}</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Bottom Input Area */}
            <footer className="p-4 border-t border-zinc-800/80 bg-zinc-950">
              <div className="max-w-3xl mx-auto">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendMessage();
                  }}
                  className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-2 focus-within:border-zinc-700 transition-all shadow-lg"
                >
                  <input
                    type="text"
                    value={inputQuery}
                    onChange={(e) => setInputQuery(e.target.value)}
                    placeholder="Ask about architecture, auth flows, cross-repo dependencies (Enter to send)..."
                    disabled={isStreaming}
                    className="flex-1 bg-transparent px-3 py-1.5 text-sm text-white placeholder-zinc-500 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={isStreaming || !inputQuery.trim()}
                    className="p-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 text-black font-semibold rounded-xl transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>

                <div className="flex items-center justify-between text-[11px] text-zinc-400 mt-2 px-1">
                  <span>Cmd/Ctrl+K for quick actions</span>
                  <span>Safety: Zero live code execution. All repos indexed as text.</span>
                </div>
              </div>
            </footer>
          </div>
        )}
      </main>

      {/* RIGHT PANEL: REPO EXPLORER */}
      {showExplorer && activeTab === 'chat' && (
        <aside className="w-80 flex-shrink-0 h-full overflow-hidden">
          <RepoExplorer 
            repos={repos}
            selectedRepo={explorerRepo}
            onSelectRepo={(r) => setExplorerRepo(r)}
          />
        </aside>
      )}

      {/* Add Repo Modal */}
      <AddRepoModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleAddRepo}
        limits={limits}
      />
    </div>
  );
}
