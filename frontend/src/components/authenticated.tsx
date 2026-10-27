"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, errorMessage, roleLabels, type User } from "@/lib/api";

type Auth = { user: User; logout: () => Promise<void>; error: string; busy: boolean };
const AuthContext = createContext<Auth | null>(null);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("需要登录后使用");
  return value;
}

export function Authenticated({ children, permission }: { children: ReactNode; permission?: string }) {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const refresh = useCallback(async () => {
    try {
      const result = await api<User>("/auth/me");
      setError("");
      setUser(result);
      if (permission && !result.permissions.includes(permission)) router.replace("/");
    } catch (cause) {
      setUser(null);
      if (cause instanceof ApiError && cause.status === 401) router.replace("/login");
      else setError(errorMessage(cause));
    }
  }, [permission, router]);
  useEffect(() => {
    void refresh();
    const expired = () => { setUser(null); router.replace("/login"); };
    const visible = () => { if (document.visibilityState === "visible") void refresh(); };
    const timer = setInterval(() => { if (document.visibilityState === "visible") void refresh(); }, 60000);
    const channel = new BroadcastChannel("bencao-auth");
    channel.onmessage = () => { void refresh(); };
    document.addEventListener("visibilitychange", visible);
    window.addEventListener("bencao-auth-expired", expired);
    return () => { clearInterval(timer); channel.close(); document.removeEventListener("visibilitychange", visible); window.removeEventListener("bencao-auth-expired", expired); };
  }, [refresh, router]);
  async function logout() {
    setBusy(true);
    setError("");
    try {
      await api<void>("/auth/logout", { method: "POST" });
      const channel = new BroadcastChannel("bencao-auth");
      channel.postMessage("logout");
      channel.close();
      setUser(null);
      router.replace("/login");
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  if (!user || (permission && !user.permissions.includes(permission))) return (
    <main className="auth-loading" aria-live="polite">
      <h1>本草知问</h1>
      <p>{error || "正在验证登录状态…"}</p>
      {error && <button className="auth-primary" onClick={() => { setError(""); void refresh(); }}>重新连接</button>}
      {error && <Link href="/login">返回登录</Link>}
    </main>
  );
  return <AuthContext.Provider value={{ user, logout, error, busy }}>{children}</AuthContext.Provider>;
}

export function AccountNavigation() {
  const { user, logout, busy, error } = useAuth();
  return (
    <div className="account-navigation">
      <Link href="/account" className="account-identity"><span>{user.display_name}</span><small>{roleLabels[user.role]} · {user.username}</small></Link>
      {user.permissions.includes("users:manage") && <Link href="/admin" className="account-link">账号管理</Link>}
      <button className="account-link" onClick={() => void logout()} disabled={busy}>{busy ? "退出中…" : "退出登录"}</button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  );
}

export function AccountHeader({ title }: { title: string }) {
  return <header className="account-header"><div><Link href="/">← 返回知识库</Link><h1>{title}</h1></div><AccountNavigation /></header>;
}
