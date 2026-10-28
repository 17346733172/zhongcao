"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, errorMessage, roleDescriptions, roleLabels } from "@/lib/api";
import { AccountHeader, useAuth } from "./authenticated";
export default function AccountSettings() {
  const { user } = useAuth();
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    if (password !== confirm) { setError("两次输入的新密码不一致。"); return; }
    setBusy(true);
    try {
      await api<void>("/auth/password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, password }) });
      const channel = new BroadcastChannel("bencao-auth"); channel.postMessage("password-changed"); channel.close();
      router.replace("/login");
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  return <main className="account-page"><AccountHeader title="我的账号" /><section className="account-card account-settings"><h2>{user.display_name}</h2><p className="section-description">{user.username} · {roleLabels[user.role]}</p><p className="account-permissions">{roleDescriptions[user.role]}</p><h3>修改密码</h3><p className="section-description">修改后需重新登录，其他设备的登录也会失效。</p><form className="auth-form" onSubmit={submit} aria-busy={busy}>
    <label htmlFor="current-password">原密码</label><input id="current-password" type="password" autoComplete="current-password" required maxLength={128} value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} disabled={busy} />
    <label htmlFor="changed-password">新密码</label><input id="changed-password" type="password" autoComplete="new-password" required minLength={10} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />
    <label htmlFor="confirm-password">确认新密码</label><input id="confirm-password" type="password" autoComplete="new-password" required minLength={10} maxLength={128} value={confirm} onChange={(event) => setConfirm(event.target.value)} disabled={busy} />
    {error && <p className="form-error" role="alert">{error}</p>}<button className="auth-primary" disabled={busy}>{busy ? "正在修改…" : "修改密码并重新登录"}</button>
  </form></section></main>;
}
