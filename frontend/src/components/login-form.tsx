"use client";

import { BookOpenTextIcon, EyeIcon, EyeSlashIcon, LockKeyIcon, ShieldCheckIcon } from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage, type User } from "@/lib/api";

export default function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; api<User>("/auth/me").then(() => { if (active) router.replace("/"); }).catch(() => {}); return () => { active = false; }; }, [router]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api<User>("/auth/login", { method: "POST", body: JSON.stringify({ username: username.trim(), password }) });
      setPassword("");
      router.replace("/");
      router.refresh();
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  return (
    <main className="login-page">
      <section className="login-story" aria-label="本草知问介绍">
        <div className="brand"><BookOpenTextIcon size={35} weight="fill" aria-hidden="true" /><span>本草知问</span></div>
        <div className="login-story-content"><span className="eyebrow">中药知识 · 有据可循</span><h1>让每一次提问，<br />都有原文可依。</h1><p>整理中药资料，回到知识源头。<br />在专属知识库中阅读、提问与核对。</p><div className="login-illustration" aria-hidden="true"><BookOpenTextIcon size={100} weight="light" /><span>本草 · 知识 · 问答</span></div></div>
        <p className="login-story-footer"><ShieldCheckIcon size={19} aria-hidden="true" />账号访问控制 · 按角色分配权限</p>
      </section>
      <section className="login-form-area" aria-labelledby="login-title">
        <div className="login-card"><span className="login-lock"><LockKeyIcon size={26} aria-hidden="true" /></span><h2 id="login-title">登录本草知问</h2><p className="login-subtitle">欢迎回来，继续你的知识探索</p>
          <form onSubmit={submit} className="auth-form" aria-busy={busy}>
            <label htmlFor="username">账号</label><input id="username" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={32} value={username} onChange={(event) => setUsername(event.target.value)} placeholder="请输入登录账号" disabled={busy} />
            <label htmlFor="password">密码</label><div className="password-field"><input id="password" name="password" type={visible ? "text" : "password"} autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="请输入密码" disabled={busy} aria-describedby={error ? "login-error" : undefined} /><button className="icon-button" type="button" aria-label={visible ? "隐藏密码" : "显示密码"} aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? <EyeSlashIcon size={21} /> : <EyeIcon size={21} />}</button></div>
            {error && <p className="form-error" id="login-error" role="alert">{error}</p>}
            <button className="auth-primary" type="submit" disabled={busy || !username.trim() || !password}>{busy ? "正在登录…" : "登录"}</button>
          </form>
          <p className="login-help">请使用管理员分配的账号。忘记密码请联系管理员。</p>
          <div className="login-note"><ShieldCheckIcon size={19} aria-hidden="true" /><p>不同账号拥有不同操作权限，登录后可查看自己的角色。</p></div>
        </div><p className="login-bottom">资料问答仍为演示，请核对引用原文</p>
      </section>
    </main>
  );
}
