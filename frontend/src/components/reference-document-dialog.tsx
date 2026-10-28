"use client";

import { useEffect, useState } from "react";
import { errorMessage } from "@/lib/api";
import { herbalReferenceDocument, loadHerbalReferenceDocument } from "@/lib/reference-document";
import type { Source } from "@/lib/types";
import { SourceDialog } from "./source-dialog";

type State =
  | { status: "loading" }
  | { status: "ready"; document: Source }
  | { status: "error"; message: string };

export function ReferenceDocumentDialog({ onClose }: { onClose: () => void }) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    loadHerbalReferenceDocument(controller.signal).then((document) => {
      if (!controller.signal.aborted) setState({ status: "ready", document });
    }).catch((cause) => {
      if (!controller.signal.aborted) setState({ status: "error", message: errorMessage(cause) });
    });
    return () => controller.abort();
  }, [attempt]);
  function retry() {
    setState({ status: "loading" });
    setAttempt((current) => current + 1);
  }
  return <SourceDialog source={state.status === "ready" ? state.document : herbalReferenceDocument} loading={state.status === "loading"} error={state.status === "error" ? state.message : undefined} onRetry={retry} onClose={onClose} />;
}
