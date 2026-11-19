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

export type AnswerToolCall = {
  name: string;
  title: string;
  action: string;
  status?: "success" | "error";
  summary?: string;
  durationMs?: number;
  fetchedAt?: string;
  stale?: boolean;
};

export type AnswerChart = {
  title: string;
  unit: string;
  categories: string[];
  series: { name: string; values: number[] }[];
  source?: string;
  fetchedAt?: string | null;
  stale?: boolean;
};

export type Answer = {
  toolCalls?: AnswerToolCall[];
  charts?: AnswerChart[];
  usage?: { inputTokens: number; outputTokens: number; scope?: "tool_selection" };
  mode?: "extract" | "generated" | "no_match" | "clarification" | "greeting" | "data_center";
  dataCenter?: DataCenterTarget;
  resolvedQuestion?: string;
  model?: string;
  retrievalMethod?: "vector";
  retrievedSources?: Source[];
  title: string;
  introduction: string;
  sections: AnswerSection[];
  sources: Source[];
};

export type DataCenterTarget = {
  tab: "overview" | "devices" | "prescriptions";
  kind?: string;
  status?: string;
  deviceId?: string;
  alarmStatus?: string;
  section?: "alarms";
};

export type Message = {
  id: string;
  question: string;
  time: string;
  answeredAt?: string;
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
