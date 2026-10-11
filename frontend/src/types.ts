export interface Repo {
  id: string;
  workspace_id: string;
  url: string;
  owner: string;
  name: string;
  branch: string;
  commit_sha?: string;
  status: 'queued' | 'cloning' | 'parsing' | 'embedding' | 'ready' | 'failed';
  progress: number;
  status_message?: string;
  size_stats?: {
    file_count?: number;
    loc?: number;
    chunk_count?: number;
    skipped_files?: number;
  };
  summary?: string;
  error?: string;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  created_at: string;
}

export interface AgentStep {
  step: number;
  action: string;
  status: string;
  input?: any;
  result_count?: number;
  symbols_found?: string[];
  references_count?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  steps?: AgentStep[];
  structuredData?: any;
  mode?: string;
}

export interface SystemLimits {
  max_repo_size_mb: number;
  max_repo_files: number;
  max_indexed_loc: number;
  max_file_size_kb: number;
  max_repos_per_workspace: number;
  max_concurrent_jobs: number;
}
