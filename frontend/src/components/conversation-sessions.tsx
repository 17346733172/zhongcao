"use client";

import { ChatCircleDotsIcon, ClockCounterClockwiseIcon, PlusIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, type KeyboardEvent } from "react";
import type { Conversation } from "@/lib/types";

type Props = {
  conversations: Conversation[];
  activeId: string | null;
  open: boolean;
  loading?: boolean;
  saving?: boolean;
  unsaved?: boolean;
  onNew: () => void;
  onSelect: (id: string) => void;
  onClose: () => void;
};

export function ConversationSessions({ conversations, activeId, open, loading = false, saving = false, unsaved = false, onNew, onSelect, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!open || !dialog) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    return () => { dialog.close(); previous?.focus({ preventScroll: true }); };
  }, [open]);

  function containFocus(event: KeyboardEvent<HTMLDialogElement>) {
    if (event.key !== "Tab") return;
    const controls = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not([disabled])"));
    const first = controls[0], last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }

  const now = Date.now();
  const dayFormat = new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" });
  const timeFormat = new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const today = dayFormat.format(now), yesterday = dayFormat.format(now - 86_400_000);
  const latestAt = (conversation: Conversation) => conversation.messages.at(-1)?.answeredAt ?? conversation.updatedAt;
  const sorted = [...conversations].sort((a, b) => (Date.parse(latestAt(b) ?? "") || 0) - (Date.parse(latestAt(a) ?? "") || 0));
  function groupOf(conversation: Conversation) {
    const value = Date.parse(latestAt(conversation) ?? "");
    if (!Number.isFinite(value)) return "本页会话";
    const day = dayFormat.format(value);
    return day === today ? "今天" : day === yesterday ? "昨天" : "更早";
  }

  function content(mobile: boolean) {
    return <>
      <header className="session-panel-heading">
        <h2 id={mobile ? "session-dialog-title" : "session-panel-title"}>会话</h2>
        {mobile && <button className="icon-button" aria-label="关闭会话窗口" onClick={onClose}><XIcon size={20} aria-hidden="true" /></button>}
      </header>
      <div className="session-panel-content">
        <button className="session-new" disabled={loading} onClick={onNew}><PlusIcon size={20} aria-hidden="true" />新会话</button>
        <div className="session-history-heading"><ClockCounterClockwiseIcon size={18} aria-hidden="true" /><h3>历史会话</h3><span>{conversations.length}</span></div>
        <nav className="session-history-list" aria-label="历史会话" aria-busy={loading}>
          {["今天", "昨天", "更早", "本页会话"].map((group) => {
            const items = sorted.filter((conversation) => groupOf(conversation) === group);
            return items.length > 0 && <section className="session-day-group" key={group} aria-label={group}>
              <h4>{group}</h4>
              {items.map((conversation) => {
                const latest = conversation.messages.at(-1);
                const timestamp = Date.parse(latestAt(conversation) ?? "");
                const time = Number.isFinite(timestamp) ? timeFormat.format(timestamp) : latest?.time;
                return <button className={"session-history-item" + (conversation.id === activeId ? " active" : "")} key={conversation.id} aria-current={conversation.id === activeId ? "true" : undefined} title={conversation.title} onClick={() => onSelect(conversation.id)}>
                  <span className="session-history-title"><ChatCircleDotsIcon size={17} aria-hidden="true" /><span>{conversation.title}</span></span>
                  <span className="session-history-meta"><time dateTime={Number.isFinite(timestamp) ? latestAt(conversation) : undefined}>{time}</time><span>{conversation.messageCount ?? conversation.messages.length} 轮</span></span>
                </button>;
              })}
            </section>;
          })}
          {!conversations.length && <div className="session-history-empty"><ChatCircleDotsIcon size={28} aria-hidden="true" /><p>{loading ? "正在读取历史会话…" : "暂无历史会话"}</p><span>{loading ? "请稍候" : "发送消息后，会话会显示在这里"}</span></div>}
        </nav>
        <p className="session-retention-note">{saving ? "正在保存会话…" : unsaved ? "会话尚未保存，请重试保存后再离开。" : "历史会话保存在当前账号，刷新后可继续。"}</p>
      </div>
    </>;
  }

  return <>
    <aside className="session-panel" aria-labelledby="session-panel-title">{content(false)}</aside>
    <dialog ref={dialogRef} className="session-dialog" id="conversation-sessions-dialog" aria-labelledby="session-dialog-title" onKeyDown={containFocus} onCancel={onClose} onClose={onClose} onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>{content(true)}</dialog>
  </>;
}
