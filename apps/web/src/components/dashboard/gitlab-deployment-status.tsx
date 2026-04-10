'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  GitBranch,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  ExternalLink,
  GitCommit,
  Rocket,
  RefreshCw,
  AlertCircle,
  Play,
  GitlabIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiClient } from '@/lib/api-client';
import { formatDistanceToNow } from 'date-fns';

type PipelineStatus = 'success' | 'failed' | 'running' | 'pending' | 'canceled' | 'skipped' | 'manual';

interface GitLabStatusData {
  connected: boolean;
  project_name?: string;
  project_url?: string;
  default_branch?: string;
  latest_pipeline?: {
    id: number;
    status: string;
    ref: string;
    sha: string;
    web_url: string;
    created_at: string;
    source: string;
  };
  latest_commit?: {
    sha: string;
    short_sha: string;
    title: string;
    author_name: string;
    authored_date: string;
    web_url: string;
  };
  pipeline_jobs: Array<{
    id: number;
    name: string;
    stage: string;
    status: string;
    web_url: string;
    duration?: number;
  }>;
  latest_deployment?: {
    id: number;
    status: string;
    environment: string;
    ref: string;
    sha: string;
    created_at: string;
    deployed_by?: string;
  };
  error?: string;
}

const statusConfig: Record<PipelineStatus, { color: string; bg: string; icon: React.ReactNode; label: string }> = {
  success: {
    color: 'text-green-400',
    bg: 'bg-green-500/10 border-green-500/30',
    icon: <CheckCircle2 className="w-4 h-4" />,
    label: 'Passed',
  },
  failed: {
    color: 'text-red-400',
    bg: 'bg-red-500/10 border-red-500/30',
    icon: <XCircle className="w-4 h-4" />,
    label: 'Failed',
  },
  running: {
    color: 'text-blue-400',
    bg: 'bg-blue-500/10 border-blue-500/30',
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
    label: 'Running',
  },
  pending: {
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/10 border-yellow-500/30',
    icon: <Clock className="w-4 h-4" />,
    label: 'Pending',
  },
  canceled: {
    color: 'text-gray-400',
    bg: 'bg-gray-500/10 border-gray-500/30',
    icon: <XCircle className="w-4 h-4" />,
    label: 'Canceled',
  },
  skipped: {
    color: 'text-gray-400',
    bg: 'bg-gray-500/10 border-gray-500/30',
    icon: <AlertCircle className="w-4 h-4" />,
    label: 'Skipped',
  },
  manual: {
    color: 'text-purple-400',
    bg: 'bg-purple-500/10 border-purple-500/30',
    icon: <Play className="w-4 h-4" />,
    label: 'Manual',
  },
};

export function GitLabDeploymentStatus() {
  const [data, setData] = useState<GitLabStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const result = await apiClient.getGitLabStatus();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch GitLab status');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll every 30 seconds
    const interval = setInterval(() => fetchStatus(true), 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading GitLab status...</span>
        </div>
      </div>
    );
  }

  if (error || !data?.connected) {
    return (
      <div className="rounded-xl border border-orange-500/30 bg-orange-500/5 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitlabIcon className="w-5 h-5 text-orange-400" />
            <span className="text-sm text-orange-300">GitLab not configured</span>
          </div>
          <span className="text-xs text-gray-500">Set GITLAB_TOKEN & GITLAB_PROJECT_ID</span>
        </div>
      </div>
    );
  }

  const pipeline = data.latest_pipeline;
  const commit = data.latest_commit;
  const deployment = data.latest_deployment;
  const pipelineStatus = (pipeline?.status || 'pending') as PipelineStatus;
  const config = statusConfig[pipelineStatus] || statusConfig.pending;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-white/10 bg-gradient-to-br from-white/5 to-transparent overflow-hidden"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
            <GitlabIcon className="w-4 h-4 text-orange-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-white">GitLab CI/CD</h3>
            <a
              href={data.project_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gray-400 hover:text-orange-400 transition-colors flex items-center gap-1"
            >
              {data.project_name}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
        <button
          onClick={() => fetchStatus(true)}
          disabled={refreshing}
          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
        </button>
      </div>

      {/* Pipeline Status */}
      {pipeline && (
        <div className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={cn("p-1.5 rounded-lg border", config.bg)}>
                <span className={config.color}>{config.icon}</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className={cn("text-sm font-medium", config.color)}>
                    Pipeline {config.label}
                  </span>
                  <span className="text-xs text-gray-500">#{pipeline.id}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <GitBranch className="w-3 h-3" />
                  <span>{pipeline.ref}</span>
                  <span className="text-gray-600">|</span>
                  <span>{formatDistanceToNow(new Date(pipeline.created_at), { addSuffix: true })}</span>
                </div>
              </div>
            </div>
            <a
              href={pipeline.web_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1"
            >
              View
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          {/* Pipeline Jobs */}
          {data.pipeline_jobs.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {data.pipeline_jobs.map((job) => {
                const jobConfig = statusConfig[job.status as PipelineStatus] || statusConfig.pending;
                return (
                  <a
                    key={job.id}
                    href={job.web_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      "px-2 py-1 rounded text-xs flex items-center gap-1.5 border transition-colors hover:opacity-80",
                      jobConfig.bg
                    )}
                    title={`${job.stage}: ${job.name}`}
                  >
                    <span className={jobConfig.color}>{jobConfig.icon}</span>
                    <span className="text-gray-300">{job.name}</span>
                    {job.duration && (
                      <span className="text-gray-500">
                        {Math.round(job.duration)}s
                      </span>
                    )}
                  </a>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Latest Commit */}
      {commit && (
        <div className="px-4 py-3 border-t border-white/10 bg-white/[0.02]">
          <div className="flex items-start gap-2">
            <GitCommit className="w-4 h-4 text-gray-400 mt-0.5" />
            <div className="flex-1 min-w-0">
              <a
                href={commit.web_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-200 hover:text-white transition-colors line-clamp-1"
              >
                {commit.title}
              </a>
              <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                <span className="font-mono text-orange-400/80">{commit.short_sha}</span>
                <span>by {commit.author_name}</span>
                <span>{formatDistanceToNow(new Date(commit.authored_date), { addSuffix: true })}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Latest Deployment */}
      {deployment && (
        <div className="px-4 py-3 border-t border-white/10 bg-gradient-to-r from-green-500/5 to-transparent">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Rocket className="w-4 h-4 text-green-400" />
              <div>
                <span className="text-sm text-green-300">Deployed to {deployment.environment}</span>
                <div className="text-xs text-gray-500">
                  {formatDistanceToNow(new Date(deployment.created_at), { addSuffix: true })}
                  {deployment.deployed_by && ` by ${deployment.deployed_by}`}
                </div>
              </div>
            </div>
            <span className="text-xs font-mono text-gray-400">{deployment.sha}</span>
          </div>
        </div>
      )}
    </motion.div>
  );
}
