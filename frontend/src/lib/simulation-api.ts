import { api } from "./api";
import type { Snapshot } from "./data-center-api";

export type SimulationAction = "scenarios" | "start" | "pause";
export type SimulationStatus = { clock: Snapshot["clock"]; fetched_at: string };
export type SimulationResult = {
  action: SimulationAction; fetched_at: string; clock: Snapshot["clock"] | null;
  count: number | null; batch_ids: string[];
};
export const readSimulationStatus = (signal: AbortSignal) => api<SimulationStatus>("/simulation/status", { signal });
export const controlSimulation = (action: SimulationAction, count: number, signal: AbortSignal) =>
  api<SimulationResult>(`/simulation/${action}`, {
    method: "POST", signal,
    ...(action === "scenarios" ? { body: JSON.stringify({ count }) } : {}),
  });
