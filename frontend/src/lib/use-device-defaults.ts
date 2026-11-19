"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "./api";
import { readDeviceDefaults, saveDeviceDefault, type DeviceDefaults } from "./device-defaults-api";

export function useDeviceDefaults(onBusyChange: (busy: boolean) => void, onSaved: () => void) {
  const [data, setData] = useState<DeviceDefaults | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [reading, setReading] = useState(true);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [mustReload, setMustReload] = useState(false);
  const [readFailed, setReadFailed] = useState(false);
  const request = useRef<AbortController | null>(null);
  const baseline = useRef<DeviceDefaults | null>(null);

  const reload = useCallback(async (force = false) => {
    if (request.current) return;
    const controller = new AbortController(); request.current = controller;
    setReading(true); setError(""); setSuccess("");
    try {
      const result = await readDeviceDefaults(AbortSignal.any([controller.signal, AbortSignal.timeout(45000)]), force);
      if (controller.signal.aborted) return;
      const previousData = baseline.current;
      baseline.current = result;
      setData(result); setMustReload(!!result.stale || !!result.error || !!result.capability_pending);
      setError(result.error || (result.stale ? "设备默认用时数据已过期，当前保留上次读取结果。" : ""));
      setReadFailed(!!result.stale || !!result.error || !!result.capability_pending);
      setDrafts(previous => Object.fromEntries(result.items.map(item => {
        const old = previousData?.items.find(entry => entry.kind === item.kind);
        const edited = old && previous[item.kind] != null && (previous[item.kind].trim() === "" || Math.abs(Number(previous[item.kind]) * 60 - old.default_processing_seconds) > 0.00001);
        return [item.kind, edited ? previous[item.kind] : String(Number((item.default_processing_seconds / 60).toFixed(6)))];
      })));
    } catch (cause) { if (!controller.signal.aborted) { setError(errorMessage(cause)); setMustReload(true); setReadFailed(true); } }
    finally { if (request.current === controller) request.current = null; if (!controller.signal.aborted) setReading(false); }
  }, []);

  useEffect(() => { void reload(); return () => { request.current?.abort(); request.current = null; }; }, [reload]);
  useEffect(() => {
    if (!readFailed || reading || pending) return;
    const timer = setTimeout(() => void reload(), 15000);
    return () => clearTimeout(timer);
  }, [readFailed, reading, pending, reload]);

  async function save(kind: string) {
    const minutes = Number(drafts[kind]);
    if (request.current || !data?.supported || data.revision == null || mustReload || !drafts[kind]?.trim() || !Number.isFinite(minutes) || minutes < 0.1 || minutes > 120) return;
    const controller = new AbortController(); request.current = controller;
    setPending(kind); onBusyChange(true); setError(""); setSuccess("");
    setReadFailed(false);
    try {
      const seconds = Number((minutes * 60).toFixed(6));
      const result = await saveDeviceDefault(kind, seconds, data.revision, AbortSignal.any([controller.signal, AbortSignal.timeout(25000)]));
      if (controller.signal.aborted) return;
      baseline.current = result;
      setData(result); setSuccess(`已保存${result.items.find(item => item.kind === kind)?.name ?? "设备"}默认每次用时：${minutes} 分钟。`); onSaved();
    } catch (cause) {
      if (!controller.signal.aborted) { setError(`${errorMessage(cause)} 请重新读取并核对当前值后再保存。`); setMustReload(true); }
    } finally {
      if (request.current === controller) request.current = null;
      if (!controller.signal.aborted) { setPending(null); onBusyChange(false); }
    }
  }
  return { data, drafts, reading, pending, error, success, mustReload, readFailed, reload, save,
    edit: (kind: string, value: string) => { setDrafts(previous => ({ ...previous, [kind]: value })); setSuccess(""); },
    reset: (kind: string) => { const item = data?.items.find(item => item.kind === kind); if (item) setDrafts(previous => ({ ...previous, [kind]: String(Number((item.default_processing_seconds / 60).toFixed(6))) })); setSuccess(""); } };
}
