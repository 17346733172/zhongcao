"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "./api";
import { readSnapshot, type SnapshotState } from "./data-center-api";

export function useDataCenterSnapshot(enabled: boolean) {
  const [state, setState] = useState<SnapshotState>({ data: null, fetched_at: null, refreshing: false, stale: false, error: null });
  const [busy, setBusy] = useState(true);
  const [slowConnection, setSlowConnection] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const forceNext = useRef(false);
  const refreshData = useCallback(() => {
    forceNext.current = true;
    setRefresh(value => value + 1);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    setSlowConnection(false);
    const timer = setTimeout(() => setSlowConnection(true), 5000);
    return () => clearTimeout(timer);
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      setBusy(true);
      let pollingDelay = 15000;
      const force = forceNext.current;
      forceNext.current = false;
      try {
        const result = await readSnapshot(AbortSignal.any([controller.signal, AbortSignal.timeout(5000)]), force);
        if (controller.signal.aborted) return;
        setState(result);
        if (result.refreshing) pollingDelay = 1000;
      } catch (error) {
        if (!controller.signal.aborted) setState(previous => ({ ...previous, refreshing: false, error: errorMessage(error), stale: !!previous.data }));
      } finally {
        if (!controller.signal.aborted) {
          setBusy(false);
          timer = setTimeout(load, pollingDelay);
        }
      }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [enabled, refresh]);

  return { state, busy, slowConnection, refresh, refreshData };
}

export type DataCenterSnapshotReader = ReturnType<typeof useDataCenterSnapshot>;
