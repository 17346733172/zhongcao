export type DocumentStatus = "queued" | "parsing" | "ready" | "needs-parser" | "error";

export type KnowledgeDocument = {
  id: string;
  libraryId: string;
  name: string;
  status: DocumentStatus;
  progress: number;
  content: string;
  demo: boolean;
  stored?: boolean;
  error?: string;
};

export type DocumentBlock =
  | { type: "paragraph"; text: string }
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "table"; rows: string[][] };

export type Source = {
  id: string;
  name: string;
  page?: number;
  excerpt: string;
  fullText: string;
  demo: boolean;
  blocks?: DocumentBlock[];
  downloadUrl?: string;
};

export type AnswerMode = "ai" | "both";

export type AnswerSection = {
  title: string;
  content: string;
  origin?: "document" | "ai_supplement";
  sourceIndex?: number;
  sourceIndices?: number[];
};

export type Answer = {
  mode?: "extract" | "generated" | "no_match" | "clarification" | "greeting";
  resolvedQuestion?: string;
  model?: string;
  title: string;
  introduction: string;
  sections: AnswerSection[];
  sources: Source[];
};

export type Message = {
  id: string;
  question: string;
  time: string;
  answer: Answer;
  showSources: boolean;
  originalAnswer?: Answer;
};

export type Conversation = {
  id: string;
  libraryId: string;
  title: string;
  messages: Message[];
};
