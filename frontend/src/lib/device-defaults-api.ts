import { api } from "./api";

export type DeviceDefault = { kind: string; name: string; default_processing_seconds: number };
export type DeviceDefaults = { items: DeviceDefault[]; revision: number | null; supported: boolean | null; fetched_at: string; notice: string; stale: boolean; error: string | null; capability_pending: boolean };
export const readDeviceDefaults = (signal: AbortSignal, refresh = false) => api<DeviceDefaults>(`/simulation/device-defaults${refresh ? "?refresh=true" : ""}`, { signal });
export const saveDeviceDefault = (kind: string, seconds: number, revision: number, signal: AbortSignal) => api<DeviceDefaults>(`/simulation/device-defaults/${encodeURIComponent(kind)}`, { method: "POST", signal, body: JSON.stringify({ default_processing_seconds: seconds, expected_revision: revision }) });
