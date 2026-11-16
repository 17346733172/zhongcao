"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "@/lib/api";
import { controlSimulation, readSimulationStatus, type SimulationAction, type SimulationStatus } from "@/lib/simulation-api";

export function useSimulationControls() {
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [readError, setReadError] = useState("");
  const [operationError, setOperationError] = useState("");
  const [success, setSuccess] = useState("");
  const [pending, setPending] = useState<SimulationAction | null>(null);
  const [retry, setRetry] = useState(0);
  const active = useRef<AbortController | null>(null);
  const version = useRef(0);

  useEffect(() => () => active.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      const startedVersion = version.current;
      try {
        if (!active.current) {
          const result = await readSimulationStatus(AbortSignal.any([controller.signal, AbortSignal.timeout(25000)]));
          if (!controller.signal.aborted && startedVersion === version.current && !active.current) {
            setStatus(result); setReadError("");
          }
        }
      } catch (cause) {
        if (!controller.signal.aborted && startedVersion === version.current) setReadError(errorMessage(cause));
      } finally { if (!controller.signal.aborted) timer = setTimeout(load, 15000); }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [retry]);

  const execute = useCallback(async (action: SimulationAction, count: number) => {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    version.current += 1;
    setPending(action); setOperationError(""); setSuccess("");
    try {
      const result = await controlSimulation(action, count, AbortSignal.any([controller.signal, AbortSignal.timeout(25000)]));
      if (controller.signal.aborted) return;
      if (result.clock) {
        setStatus({ clock: result.clock, fetched_at: result.fetched_at }); setReadError("");
      }
      setSuccess(action === "scenarios" ? `已生成 ${result.count} 个匿名演示批次。可点击「开始」运行；平台已在运行时将自动调度。` : action === "start" ? "仿真已开始，按真实时间 1 倍速运行。" : "仿真已暂停，工序进度已保留。");
    } catch (cause) {
      if (!controller.signal.aborted) setOperationError(`${errorMessage(cause)} 如遇连接中断，请先确认平台状态与批次数量，避免重复提交。`);
    } finally {
      active.current = null;
      if (!controller.signal.aborted) { setPending(null); setRetry(value => value + 1); }
    }
  }, []);

  return { status, readError, operationError, success, pending, execute, reload: () => setRetry(value => value + 1) };
}
