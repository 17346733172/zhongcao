"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "./api";
import { listConversations, readConversation, saveConversationMessage } from "./conversations-api";
import type { Conversation, Message } from "./types";

type Pending = { id: string; libraryId: string; message: Message };

export function useConversationHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [unsaved, setUnsaved] = useState(false);
  const request = useRef<AbortController | null>(null);
  const pending = useRef<Pending | null>(null);
  const savingRef = useRef(false);
  const mounted = useRef(false);
  const listed = useRef(false);

  const loadHistory = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true); setLoadError("");
    try {
      const items = await listConversations(controller.signal);
      if (controller.signal.aborted) return;
      listed.current = true;
      setConversations(items);
      const id = items[0]?.id ?? null;
      setActiveId(id);
      if (id) {
        const conversation = await readConversation(id, controller.signal);
        if (!controller.signal.aborted) setConversations(current => current.map(item => item.id === id ? conversation : item));
      }
    } catch (cause) {
      if (!controller.signal.aborted) setLoadError(errorMessage(cause));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void loadHistory();
    return () => { mounted.current = false; request.current?.abort(); };
  }, [loadHistory]);

  useEffect(() => {
    if (!unsaved) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [unsaved]);

  async function select(id: string | null) {
    request.current?.abort();
    setActiveId(id); setLoadError(""); setLoading(false);
    if (!id || pending.current?.id === id) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    try {
      const conversation = await readConversation(id, controller.signal);
      if (!controller.signal.aborted) setConversations(current => current.map(item => item.id === id ? conversation : item));
    } catch (cause) {
      if (!controller.signal.aborted) setLoadError(errorMessage(cause));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  async function retrySave() {
    const item = pending.current;
    if (!mounted.current || !item || savingRef.current) return;
    savingRef.current = true;
    setSaving(true); setSaveError("");
    try {
      await saveConversationMessage(item.id, item.libraryId, item.message);
      if (mounted.current) { pending.current = null; setUnsaved(false); }
    } catch (cause) {
      if (mounted.current) setSaveError(errorMessage(cause));
    } finally {
      savingRef.current = false;
      if (mounted.current) setSaving(false);
    }
  }

  async function append(id: string, libraryId: string, message: Message) {
    if (!mounted.current || pending.current) return;
    setConversations(current => {
      const previous = current.find(item => item.id === id);
      const conversation: Conversation = {
        id, libraryId, title: previous?.title ?? message.question.slice(0, 80),
        messages: [...(previous?.messages ?? []), message],
        messageCount: (previous?.messages.length ?? 0) + 1, updatedAt: message.answeredAt, messagesLoaded: true,
      };
      return previous ? current.map(item => item.id === id ? conversation : item) : [conversation, ...current];
    });
    setActiveId(id);
    pending.current = { id, libraryId, message };
    setUnsaved(true);
    await retrySave();
  }

  return { conversations, activeId, loading, loadError, saving, saveError, unsaved, select, append, retrySave,
    retryLoad: () => listed.current && activeId ? select(activeId) : loadHistory() };
}
