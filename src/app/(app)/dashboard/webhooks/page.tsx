"use client";

import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Edit2,
  ExternalLink,
  Eye,
  EyeOff,
  Play,
  Plus,
  Power,
  Settings2,
  Trash2,
  Webhook as WebhookIcon,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { apiClient } from "@/lib/api-client";
import { type Webhook, useWebhooks } from "@/hooks/useWebhooks";

const ALL_EVENTS = [
  "ALERT_CREATED",
  "ALERT_ASSIGNED",
  "ALERT_ACKNOWLEDGED",
  "ALERT_RESOLVED",
  "ALERT_ESCALATED",
  "FACE_DETECTED",
] as const;
type WebhookEvent = (typeof ALL_EVENTS)[number];

const eventLabels: Record<WebhookEvent, string> = {
  ALERT_CREATED: "Alert Created",
  ALERT_ASSIGNED: "Alert Assigned",
  ALERT_ACKNOWLEDGED: "Acknowledged",
  ALERT_RESOLVED: "Alert Resolved",
  ALERT_ESCALATED: "Alert Escalated",
  FACE_DETECTED: "Face Detected",
};

const eventColors: Record<WebhookEvent, string> = {
  ALERT_CREATED: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  ALERT_ASSIGNED: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  ALERT_ACKNOWLEDGED: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  ALERT_RESOLVED: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  ALERT_ESCALATED: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  FACE_DETECTED: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
};

const DISCORD_PATTERN = /^https:\/\/(discord\.com|discordapp\.com)\/api\/webhooks\//;
const SLACK_PATTERN = /^https:\/\/hooks\.slack\.com\/services\//;

function isDiscordUrl(url: string) {
  return DISCORD_PATTERN.test(url);
}

function isSlackUrl(url: string) {
  return SLACK_PATTERN.test(url);
}

function truncateUrl(url: string) {
  if (isDiscordUrl(url)) {
    const match = url.match(/^(https:\/\/discord\.com\/api\/webhooks\/\d+\/)(.+)$/);
    if (match) return `${match[1]}${match[2].slice(0, 5)}.....`;
  }
  if (isSlackUrl(url)) {
    const match = url.match(/^(https:\/\/hooks\.slack\.com\/services\/T[^/]+\/)(.+)$/);
    if (match) return `${match[1]}${match[2].slice(0, 5)}.....`;
  }
  return url;
}

function EventToggle({
  event,
  active,
  onClick,
  size = "sm",
}: {
  event: WebhookEvent;
  active: boolean;
  onClick: () => void;
  size?: "sm" | "md";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full font-medium transition-all ${
        size === "md" ? "px-3.5 py-1.5 text-sm" : "px-2.5 py-0.5 text-xs"
      } ${
        active
          ? eventColors[event]
          : "bg-neutral-100 text-neutral-400 dark:bg-neutral-700 dark:text-neutral-500 opacity-60 hover:opacity-100"
      }`}
    >
      {eventLabels[event]}
    </button>
  );
}

function DeleteModal({
  isOpen,
  onClose,
  onConfirm,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-sm rounded-2xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 p-6 shadow-xl">
        <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-100 mb-2">Delete webhook?</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5">
          This webhook will stop receiving events immediately. This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-neutral-200 dark:border-neutral-600 px-4 py-2 text-sm font-medium text-neutral-500 transition hover:bg-neutral-100 dark:hover:bg-neutral-700"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

function WebhookRow({
  webhook,
  onMutate,
}: {
  webhook: Webhook;
  onMutate: () => void;
}) {
  const [showSecret, setShowSecret] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [testing, setTesting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editEvents, setEditEvents] = useState<Set<WebhookEvent>>(
    new Set(webhook.events as WebhookEvent[])
  );
  const [editUrl, setEditUrl] = useState(webhook.url);
  const isDiscord = isDiscordUrl(webhook.url);
  const isSlack = isSlackUrl(webhook.url);

  const testWebhook = async () => {
    setTesting(true);
    try {
      const result = await apiClient.testWebhook(webhook.id);
      if (result.success) {
        toast.success(`Test delivered successfully (HTTP ${result.status})`);
      } else {
        toast.error(`Test failed: ${result.error || `HTTP ${result.status}`}`);
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to send test");
    } finally {
      setTesting(false);
    }
  };

  const toggleActive = async () => {
    try {
      await apiClient.updateWebhook(webhook.id, { active: !webhook.active });
      onMutate();
      toast.success(webhook.active ? "Webhook disabled" : "Webhook enabled");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update webhook");
    }
  };

  const saveEdit = async () => {
    if (editEvents.size === 0) {
      toast.error("Select at least one event");
      return;
    }
    try {
      await apiClient.updateWebhook(webhook.id, {
        url: editUrl !== webhook.url ? editUrl : undefined,
        events: Array.from(editEvents),
      });
      setEditing(false);
      onMutate();
      toast.success("Webhook updated");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update webhook");
    }
  };

  const cancelEdit = () => {
    setEditing(false);
    setEditEvents(new Set(webhook.events as WebhookEvent[]));
    setEditUrl(webhook.url);
  };

  const deleteWebhook = async () => {
    setShowDeleteModal(false);
    try {
      await apiClient.deleteWebhook(webhook.id);
      onMutate();
      toast.success("Webhook deleted");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to delete webhook");
    }
  };

  const toggleEditEvent = (event: WebhookEvent) => {
    const next = new Set(editEvents);
    if (next.has(event)) {
      next.delete(event);
    } else {
      next.add(event);
    }
    setEditEvents(next);
  };

  return (
    <>
      <DeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={deleteWebhook}
      />
      <motion.div
        layout
        className={`rounded-xl border p-5 transition-colors ${
          webhook.active
            ? "border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800"
            : "border-dashed border-neutral-300 dark:border-neutral-600 bg-neutral-50 dark:bg-neutral-800/50"
        }`}
      >
        {/* Top row: URL + badges */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            {isDiscord ? (
              <svg className="h-5 w-5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path className="text-[#5865F2]" d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.095 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.095 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
              </svg>
            ) : isSlack ? (
              <svg className="h-5 w-5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path className="text-[#E01E5A]" d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" />
                <path className="text-[#36C5F0]" d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" />
                <path className="text-[#2EB67D]" d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.163 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" />
                <path className="text-[#ECB22E]" d="M15.163 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.163 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.27a2.527 2.527 0 0 1-2.52-2.523 2.527 2.527 0 0 1 2.52-2.52h6.315A2.528 2.528 0 0 1 24 15.163a2.528 2.528 0 0 1-2.522 2.523h-6.315z" />
              </svg>
            ) : (
              <WebhookIcon className="h-4 w-4 text-neutral-400 flex-shrink-0" />
            )}
            {editing ? (
              <input
                type="url"
                value={editUrl}
                onChange={(e) => setEditUrl(e.target.value)}
                className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 px-2.5 py-1 text-sm text-neutral-800 dark:text-neutral-100 focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
              />
            ) : (
              <p className="text-sm font-medium text-neutral-800 dark:text-neutral-100 truncate">
                {truncateUrl(webhook.url)}
              </p>
            )}
          </div>
          {!editing && (
            <div className="flex items-center gap-2 flex-shrink-0">
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                  webhook.active
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-neutral-100 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-400"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    webhook.active ? "bg-green-500" : "bg-neutral-400"
                  }`}
                />
                {webhook.active ? "Active" : "Disabled"}
              </span>
              {isDiscord && (
                <span className="inline-flex items-center rounded-full bg-indigo-100 dark:bg-indigo-900/30 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:text-indigo-400">
                  Discord
                </span>
              )}
              {isSlack && (
                <span className="inline-flex items-center rounded-full bg-purple-100 dark:bg-purple-900/30 px-2 py-0.5 text-xs font-medium text-purple-700 dark:text-purple-400">
                  Slack
                </span>
              )}
            </div>
          )}
        </div>

        {/* Events */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {editing
            ? ALL_EVENTS.map((event) => (
                <EventToggle
                  key={event}
                  event={event}
                  active={editEvents.has(event)}
                  onClick={() => toggleEditEvent(event)}
                />
              ))
            : (webhook.events as WebhookEvent[]).map((event) => (
                <span
                  key={event}
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${eventColors[event] ?? "bg-neutral-100 text-neutral-600"}`}
                >
                  {eventLabels[event] ?? event}
                </span>
              ))}
        </div>

        {/* Secret row + action buttons */}
        <div className="mt-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-3 border-t border-neutral-100 dark:border-neutral-700/50">
          {!editing ? (
            <>
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs text-neutral-400 flex-shrink-0">Signing secret</span>
                <code className="text-xs bg-neutral-100 dark:bg-neutral-700 px-2 py-0.5 rounded font-mono text-neutral-600 dark:text-neutral-300 select-all truncate">
                  {showSecret
                    ? webhook.secret
                    : `${webhook.secret.slice(0, 12)}${"*".repeat(20)}`}
                </code>
                <button
                  onClick={() => setShowSecret(!showSecret)}
                  className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition flex-shrink-0"
                  title={showSecret ? "Hide" : "Reveal"}
                >
                  {showSecret ? (
                    <EyeOff className="h-3.5 w-3.5" />
                  ) : (
                    <Eye className="h-3.5 w-3.5" />
                  )}
                </button>
                <button
                  onClick={() => {
                    void navigator.clipboard.writeText(webhook.secret);
                    toast.success("Secret copied to clipboard");
                  }}
                  className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition flex-shrink-0"
                  title="Copy"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0 self-end sm:self-auto">
                <button
                  onClick={testWebhook}
                  disabled={testing}
                  className="flex items-center gap-1 rounded border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 px-1.5 sm:px-2 py-0.5 text-[11px] font-medium text-blue-600 dark:text-blue-400 transition hover:bg-blue-100 dark:hover:bg-blue-900/40 disabled:opacity-50"
                  title="Test"
                >
                  {testing ? (
                    <div className="h-3 w-3 animate-spin rounded-full border-2 border-blue-300 border-t-blue-600" />
                  ) : (
                    <Play className="h-3 w-3" />
                  )}
                  <span className="hidden sm:inline">Test</span>
                </button>
                <button
                  onClick={() => setEditing(true)}
                  className="flex items-center gap-1 rounded border border-neutral-200 dark:border-neutral-600 px-1.5 sm:px-2 py-0.5 text-[11px] font-medium text-neutral-600 dark:text-neutral-300 transition hover:bg-neutral-100 dark:hover:bg-neutral-700"
                  title="Edit"
                >
                  <Edit2 className="h-3 w-3" />
                  <span className="hidden sm:inline">Edit</span>
                </button>
                <button
                  onClick={toggleActive}
                  className={`flex items-center gap-1 rounded border px-1.5 sm:px-2 py-0.5 text-[11px] font-medium transition ${
                    webhook.active
                      ? "border-green-200 dark:border-green-800 text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20"
                      : "border-neutral-200 dark:border-neutral-600 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700"
                  }`}
                  title={webhook.active ? "Disable" : "Enable"}
                >
                  <Power className="h-3 w-3" />
                  <span className="hidden sm:inline">{webhook.active ? "Disable" : "Enable"}</span>
                </button>
                <button
                  onClick={() => setShowDeleteModal(true)}
                  className="flex items-center gap-1 rounded border border-neutral-200 dark:border-neutral-600 px-1.5 sm:px-2 py-0.5 text-[11px] font-medium text-neutral-400 transition hover:border-red-200 hover:text-red-500 hover:bg-red-50 dark:hover:border-red-800 dark:hover:text-red-400 dark:hover:bg-red-900/20"
                  title="Delete"
                >
                  <Trash2 className="h-3 w-3" />
                  <span className="hidden sm:inline">Delete</span>
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2 ml-auto">
              <button
                onClick={saveEdit}
                className="rounded-lg bg-neutral-800 dark:bg-neutral-100 px-3 py-1.5 text-xs font-medium text-white dark:text-neutral-800 transition hover:bg-neutral-900 dark:hover:bg-white"
              >
                Save
              </button>
              <button
                onClick={cancelEdit}
                className="rounded-lg border border-neutral-200 dark:border-neutral-600 px-3 py-1.5 text-xs font-medium text-neutral-400 transition hover:text-neutral-600 hover:bg-neutral-100 dark:hover:text-neutral-300 dark:hover:bg-neutral-700"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </>
  );
}

function CreateModal({
  isOpen,
  onClose,
  onCreated,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [newUrl, setNewUrl] = useState("");
  const [newEvents, setNewEvents] = useState<Set<WebhookEvent>>(new Set(ALL_EVENTS));

  const detectedDiscord = isDiscordUrl(newUrl);
  const detectedSlack = isSlackUrl(newUrl);

  const toggleEvent = (event: WebhookEvent) => {
    const next = new Set(newEvents);
    if (next.has(event)) {
      next.delete(event);
    } else {
      next.add(event);
    }
    setNewEvents(next);
  };

  const createWebhook = async () => {
    if (!newUrl || newEvents.size === 0) {
      toast.error("URL and at least one event are required");
      return;
    }
    try {
      await apiClient.createWebhook(newUrl, Array.from(newEvents));
      setNewUrl("");
      setNewEvents(new Set(ALL_EVENTS));
      onCreated();
      onClose();
      toast.success("Webhook created");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create webhook");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md rounded-2xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-100">
            Add Webhook Endpoint
          </h2>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5">
          We&apos;ll send an HTTP POST request to this URL whenever selected events occur.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Endpoint URL
            </label>
            <input
              type="url"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://example.com/webhooks/fazri"
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 px-3 py-2.5 text-sm text-neutral-800 dark:text-neutral-100 placeholder-neutral-400 focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            />
            {detectedDiscord && (
              <div className="mt-2 flex items-center gap-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 px-3 py-2">
                <svg className="h-4 w-4 flex-shrink-0 text-indigo-500" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.095 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.095 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
                <p className="text-xs text-indigo-700 dark:text-indigo-300">
                  Discord webhook detected — events will be sent as rich embeds with color-coded event types.
                </p>
              </div>
            )}
            {detectedSlack && (
              <div className="mt-2 flex items-center gap-2 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 px-3 py-2">
                <svg className="h-4 w-4 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                  <path className="text-[#E01E5A]" d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" />
                  <path className="text-[#36C5F0]" d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" />
                  <path className="text-[#2EB67D]" d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.163 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" />
                  <path className="text-[#ECB22E]" d="M15.163 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.163 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.27a2.527 2.527 0 0 1-2.52-2.523 2.527 2.527 0 0 1 2.52-2.52h6.315A2.528 2.528 0 0 1 24 15.163a2.528 2.528 0 0 1-2.522 2.523h-6.315z" />
                </svg>
                <p className="text-xs text-purple-700 dark:text-purple-300">
                  Slack webhook detected — events will be sent as rich messages with color-coded attachments.
                </p>
              </div>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              Subscribe to events
            </label>
            <div className="flex flex-wrap gap-2">
              {ALL_EVENTS.map((event) => (
                <EventToggle
                  key={event}
                  event={event}
                  active={newEvents.has(event)}
                  onClick={() => toggleEvent(event)}
                  size="md"
                />
              ))}
            </div>
            <p className="mt-2 text-xs text-neutral-400">Click to toggle. You can change these later.</p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg border border-neutral-200 dark:border-neutral-600 px-4 py-2 text-sm font-medium text-neutral-500 transition hover:bg-neutral-100 dark:hover:bg-neutral-700"
          >
            Cancel
          </button>
          <button
            onClick={createWebhook}
            className="rounded-lg bg-neutral-800 dark:bg-neutral-100 px-4 py-2 text-sm font-medium text-white dark:text-neutral-800 transition hover:bg-neutral-900 dark:hover:bg-white"
          >
            Create Webhook
          </button>
        </div>
      </div>
    </div>
  );
}

export default function WebhooksPage() {
  const { data: webhooks, isLoading, mutate } = useWebhooks();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);

  return (
    <>
      <CreateModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={mutate}
      />

      <div className="max-w-3xl mx-auto space-y-4">
        {/* Header card */}
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">Webhooks</h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
                Real-time event notifications for Fazri Analyzer
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-x-1.5 rounded-lg bg-neutral-800 dark:bg-neutral-100 px-4 py-2 text-center text-sm font-medium text-white dark:text-neutral-800 transition hover:bg-neutral-900 dark:hover:bg-white"
            >
              <Plus strokeWidth={2} size={16} />
              Add Endpoint
            </button>
          </div>

          <div className="mt-5">
            {isLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800 dark:border-neutral-600 dark:border-t-neutral-200" />
              </div>
            ) : !webhooks || webhooks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-neutral-400">
                <div className="rounded-full bg-neutral-100 dark:bg-neutral-700 p-4 mb-4">
                  <WebhookIcon className="h-8 w-8" />
                </div>
                <p className="text-sm font-medium text-neutral-600 dark:text-neutral-300">
                  No webhook endpoints
                </p>
                <p className="text-xs mt-1 text-center max-w-sm">
                  Add a webhook endpoint to receive real-time notifications when alerts are created,
                  assigned, resolved, escalated, or faces are detected.
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 flex items-center gap-1.5 rounded-lg bg-neutral-800 dark:bg-neutral-100 px-4 py-2 text-sm font-medium text-white dark:text-neutral-800 transition hover:bg-neutral-900 dark:hover:bg-white"
                >
                  <Plus strokeWidth={2} size={16} />
                  Add your first webhook
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {webhooks.map((webhook) => (
                  <WebhookRow key={webhook.id} webhook={webhook} onMutate={mutate} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Platforms hint */}
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <Settings2 className="h-5 w-5 text-neutral-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                Works with any HTTP endpoint
              </p>
              <p className="text-xs text-neutral-400 mt-0.5">
                Standard webhooks, Discord, Slack, Zapier, Make, Pipedream, or your own server.
                Discord and Slack webhook URLs are auto-detected and events are formatted as rich messages.
              </p>
            </div>
          </div>
        </div>

        {/* Collapsible integration guide */}
        <div>
          <button
            onClick={() => setDocsOpen(!docsOpen)}
            className="flex w-full items-center justify-between rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-6 py-4 text-left transition hover:bg-neutral-50 dark:hover:bg-neutral-750"
          >
            <div className="flex items-center gap-3">
              <ExternalLink className="h-5 w-5 text-neutral-400" />
              <div>
                <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  Integration Guide
                </p>
                <p className="text-xs text-neutral-400">Payload format, headers, and signature verification</p>
              </div>
            </div>
            {docsOpen ? (
              <ChevronUp className="h-5 w-5 text-neutral-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-neutral-400" />
            )}
          </button>

          <AnimatePresence>
            {docsOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="mt-2 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 px-6 py-5 space-y-5">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
                      Request Headers
                    </h3>
                    <div className="rounded-lg bg-neutral-50 dark:bg-neutral-900 p-4 font-mono text-xs text-neutral-600 dark:text-neutral-400 space-y-1">
                      <p>
                        <span className="text-neutral-400">Content-Type:</span> application/json
                      </p>
                      <p>
                        <span className="text-neutral-400">X-Webhook-Signature:</span> &lt;hmac-sha256-hex&gt;
                      </p>
                      <p>
                        <span className="text-neutral-400">X-Webhook-Event:</span>{" "}
                        ALERT_CREATED | ALERT_ASSIGNED | ALERT_ACKNOWLEDGED | ALERT_RESOLVED | ALERT_ESCALATED | FACE_DETECTED
                      </p>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
                      Payload
                    </h3>
                    <pre className="rounded-lg bg-neutral-50 dark:bg-neutral-900 p-4 font-mono text-xs text-neutral-600 dark:text-neutral-400 overflow-x-auto">
{`{
  "event": "ALERT_CREATED",
  "data": {
    "alert_id": "3fa85f64-...",
    "title": "Suspicious Activity Detected",
    "severity": "high",
    "zone_id": "LAB_305",
    "timestamp": "2026-03-31T10:00:00.000Z"
  },
  "timestamp": "2026-03-31T10:00:00.000Z"
}`}
                    </pre>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
                      Verify Signature (Python)
                    </h3>
                    <pre className="rounded-lg bg-neutral-50 dark:bg-neutral-900 p-4 font-mono text-xs text-neutral-600 dark:text-neutral-400 overflow-x-auto">
{`import hmac, hashlib

def verify_webhook(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)`}
                    </pre>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
                      Verify Signature (Node.js)
                    </h3>
                    <pre className="rounded-lg bg-neutral-50 dark:bg-neutral-900 p-4 font-mono text-xs text-neutral-600 dark:text-neutral-400 overflow-x-auto">
{`const crypto = require('crypto');

function verifyWebhook(rawBody, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(rawBody)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}`}
                    </pre>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  );
}
