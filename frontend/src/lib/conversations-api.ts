import { api } from "./api";
import type { Conversation, Message } from "./types";

export const listConversations = (signal: AbortSignal) => api<Conversation[]>("/conversations", { signal });
export const readConversation = (id: string, signal: AbortSignal) => api<Conversation>(`/conversations/${encodeURIComponent(id)}`, { signal });
export const saveConversationMessage = (id: string, libraryId: string, message: Message) => api<{ saved: true; messageId: string }>(`/conversations/${encodeURIComponent(id)}/messages`, {
  method: "POST", body: JSON.stringify({ libraryId, message }),
});
