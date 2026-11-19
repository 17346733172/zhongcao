"use client";

import { useEffect, useState } from "react";
import { errorMessage } from "./api";
import { DATA_CENTER_TIMEOUT_MS, readCompletedBatches, type CompletedBatchPage } from "./data-center-api";

export function useCompletedBatches() {
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<CompletedBatchPage | null>(null);
  const [busy, setBusy] = useState(true);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      setBusy(true); setSlow(false); setError("");
      const slowTimer = setTimeout(() => setSlow(true), 5000);
      try {
        const result = await readCompletedBatches(offset, AbortSignal.any([controller.signal, AbortSignal.timeout(DATA_CENTER_TIMEOUT_MS)]));
        if (controller.signal.aborted) return;
        if (offset > 0 && offset >= result.total) {
          setOffset(Math.max(0, Math.floor((result.total - 1) / 20) * 20));
          return;
        }
        setPage(result);
      } catch (error) {
        if (!controller.signal.aborted) setError(errorMessage(error));
      } finally {
        clearTimeout(slowTimer);
        if (!controller.signal.aborted) {
          setBusy(false);
          timer = setTimeout(load, 15000);
        }
      }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [offset, refresh]);

  return { page, offset, setOffset, busy, slow, error, refreshData: () => setRefresh(value => value + 1) };
}
