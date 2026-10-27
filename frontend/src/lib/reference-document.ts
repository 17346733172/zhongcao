import { api } from "./api";
import type { Source } from "./types";

export const herbalReferenceDocument: Source = {
  id: "herbal-reference",
  name: "中药基础知识（详解版）.docx",
  excerpt: "",
  fullText: "",
  demo: false,
};

export function loadHerbalReferenceDocument(signal: AbortSignal) {
  return api<Source>("/reference-document", { signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]) });
}
