export type DocumentStatus = "queued" | "parsing" | "ready" | "needs-parser" | "error";

export type KnowledgeDocument = {
  id: string;
  libraryId: string;
  name: string;
  status: DocumentStatus;
  progress: number;
  content: string;
  demo: boolean;
  error?: string;
};

export type Source = {
  id: string;
  name: string;
  page?: number;
  excerpt: string;
  fullText: string;
  demo: boolean;
};

export type AnswerSection = {
  title: string;
  content: string;
  sourceIndex: number;
};

export type Answer = {
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
};

export type Conversation = {
  id: string;
  libraryId: string;
  title: string;
  messages: Message[];
};
