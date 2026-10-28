import type { Conversation, KnowledgeDocument } from "./types";

export const libraries = [{ id: "herbal", name: "中药基础资料" }];

// 新对话和资料列表不再预置演示内容，避免将示例当成检索结果。
export const initialConversations: Conversation[] = [];
export const initialDocuments: KnowledgeDocument[] = [];
