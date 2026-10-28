export type Role = "admin" | "editor" | "viewer";
export type User = {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  active: boolean;
  permissions: string[];
};
export const roleLabels: Record<Role, string> = { admin: "管理员", editor: "编辑员", viewer: "普通用户" };
export const roleDescriptions: Record<Role, string> = {
  admin: "查看与提问、管理资料、管理账号",
  editor: "查看与提问、添加和移除资料",
  viewer: "查看资料、提问与核对原文",
};
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      credentials: "same-origin",
      cache: "no-store",
      signal: options.signal ?? AbortSignal.timeout(20000),
      headers: { ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }), "X-CSRF-Protection": "1", ...options.headers },
    });
  } catch {
    throw new ApiError(0, "暂时无法连接服务，请稍后重试。");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401) window.dispatchEvent(new Event("bencao-auth-expired"));
    throw new ApiError(response.status, typeof body?.detail === "string" ? body.detail : "服务暂时不可用，请稍后重试。");
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}
export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "操作失败，请重试。";
}
