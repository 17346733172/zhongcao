"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, errorMessage, roleDescriptions, roleLabels, type Role, type User } from "@/lib/api";
import { AccountHeader, useAuth } from "./authenticated";

function UserRow({ user, currentId, onUpdated }: { user: User; currentId: number; onUpdated: (user: User) => void }) {
  const [role, setRole] = useState<Role>(user.role);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => { setRole(user.role); }, [user.role]);
  const self = user.id === currentId;
  async function update(active = user.active) {
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await api<User>(`/users/${user.id}`, { method: "PATCH", body: JSON.stringify({ role, active }) });
      onUpdated(result);
      setNotice("账号已更新，该账号需要重新登录。");
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  async function reset(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      await api<void>(`/users/${user.id}/password`, { method: "POST", body: JSON.stringify({ password }) });
      setPassword(""); setNotice("密码已重置，旧登录已失效。请将新密码告知账号持有人。");
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  return (
    <li className="user-row" aria-busy={busy}>
      <div className="user-summary"><div><h3>{user.display_name}{self && <small>当前账号</small>}</h3><p>{user.username}</p></div><span className={"status-badge " + (user.active ? "status-active" : "status-inactive")}>{user.active ? "正常" : "已停用"}</span></div>
      <div className="user-actions"><label htmlFor={`role-${user.id}`}>账号角色</label><select id={`role-${user.id}`} value={role} onChange={(event) => setRole(event.target.value as Role)} disabled={self || busy}>{Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button className="auth-secondary" disabled={self || busy || role === user.role} onClick={() => void update()}>保存角色</button><button className="auth-secondary" disabled={self || busy} onClick={() => void update(!user.active)}>{user.active ? "停用账号" : "启用账号"}</button></div>
      {!self && <details className="reset-password"><summary>重置密码</summary><form className="user-actions" onSubmit={reset}><label htmlFor={`reset-${user.id}`}>新密码</label><input id={`reset-${user.id}`} type="password" autoComplete="new-password" minLength={10} maxLength={128} placeholder="10–128 位新密码" required value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} /><button className="auth-secondary" type="submit" disabled={busy || password.length < 10}>确认重置</button></form></details>}
      {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="form-success" role="status">{notice}</p>}
    </li>
  );
}

export default function UserManagement() {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [notice, setNotice] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const load = useCallback(async () => {
    setLoading(true); setListError("");
    try { setUsers(await api<User[]>("/users")); }
    catch (cause) { setListError(errorMessage(cause)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const created = await api<User>("/users", { method: "POST", body: JSON.stringify({ username, display_name: displayName, password, role }) });
      setUsers((current) => [...current, created]);
      setUsername(""); setDisplayName(""); setPassword(""); setRole("viewer");
      setNotice(`账号 ${created.username} 已创建，可使用分配的密码登录。`);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }
  return (
    <main className="account-page"><AccountHeader title="账号与权限管理" /><div className="admin-layout">
      <section className="account-card create-user" aria-labelledby="create-user-title"><h2 id="create-user-title">创建账号</h2><p className="section-description">为成员分配合适的操作权限。</p><form className="auth-form" onSubmit={create} aria-busy={busy}>
        <label htmlFor="new-username">登录账号</label><input id="new-username" autoComplete="off" minLength={3} maxLength={32} pattern="[a-zA-Z0-9_]+" placeholder="3–32 位字母、数字或下划线" required value={username} onChange={(event) => setUsername(event.target.value)} disabled={busy} />
        <label htmlFor="display-name">显示名称</label><input id="display-name" maxLength={50} required value={displayName} onChange={(event) => setDisplayName(event.target.value)} disabled={busy} />
        <label htmlFor="new-password">初始密码</label><input id="new-password" type="password" autoComplete="new-password" minLength={10} maxLength={128} placeholder="至少 10 位" required value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} />
        <label htmlFor="new-role">账号角色</label><select id="new-role" value={role} onChange={(event) => setRole(event.target.value as Role)} disabled={busy}>{Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><p className="field-help">{roleDescriptions[role]}</p>
        {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="form-success" role="status">{notice}</p>}<button className="auth-primary" disabled={busy}>{busy ? "正在创建…" : "创建账号"}</button>
      </form></section>
      <section className="account-card users-section" aria-labelledby="users-title"><div className="section-heading"><div><h2 id="users-title">成员账号 <small>{users.length}</small></h2><p className="section-description">角色、停用和密码变更会使该账号的旧登录失效。</p></div><button className="auth-secondary" disabled={loading} onClick={() => void load()}>刷新</button></div>
        {loading && <p className="section-description" role="status">正在读取账号…</p>}{listError && <p className="form-error" role="alert">{listError}</p>}{!loading && !listError && !users.length && <p className="section-description">暂无账号。</p>}
        <ul className="users-list">{users.map((item) => <UserRow key={item.id} user={item} currentId={user.id} onUpdated={(result) => setUsers((current) => current.map((entry) => entry.id === result.id ? result : entry))} />)}</ul>
      </section>
    </div></main>
  );
}
