"use client";

import { BookOpenTextIcon, BooksIcon, ChatTextIcon, ClockCounterClockwiseIcon, PlusCircleIcon, SidebarSimpleIcon, XIcon } from "@phosphor-icons/react";
import { AccountNavigation } from "./authenticated";
import { libraries } from "@/lib/demo-data";
import type { Conversation } from "@/lib/types";

type Props = {
  libraryId: string;
  activeId: string | null;
  conversations: Conversation[];
  open: boolean;
  onLibrary: (id: string) => void;
  onConversation: (id: string) => void;
  onNew: () => void;
  onClose: () => void;
  onCollapse: () => void;
};

export function Sidebar(props: Props) {
  const history = props.conversations.filter((item) => item.libraryId === props.libraryId);
  return (
    <aside className={"sidebar" + (props.open ? " drawer-open" : "")} aria-label="知识库与历史对话">
      <div className="brand">
        <BookOpenTextIcon size={34} weight="fill" aria-hidden="true" />
        <span>本草知问</span>
        <button className="icon-button desktop-sidebar-toggle" aria-label="收起侧栏" onClick={props.onCollapse}><SidebarSimpleIcon size={22} /></button>
        <button className="icon-button sidebar-close" aria-label="关闭导航" onClick={props.onClose}><XIcon size={21} /></button>
      </div>
      <button className="new-chat" onClick={props.onNew}>
        <PlusCircleIcon size={21} aria-hidden="true" />新建对话
      </button>
      <nav className="sidebar-navigation">
        <section aria-labelledby="library-label">
          <h2 className="nav-label" id="library-label"><BooksIcon size={21} aria-hidden="true" />知识库</h2>
          <div className="nav-list">
            {libraries.map((library) => (
              <button key={library.id} className={"nav-item" + (props.libraryId === library.id ? " active" : "")} aria-pressed={props.libraryId === library.id} aria-haspopup="dialog" onClick={() => props.onLibrary(library.id)}>
                <BookOpenTextIcon size={22} aria-hidden="true" /><span>{library.name}</span>
              </button>
            ))}
          </div>
        </section>
        <section className="history-section" aria-labelledby="history-label">
          <h2 className="nav-label" id="history-label"><ClockCounterClockwiseIcon size={23} aria-hidden="true" />历史对话</h2>
          <div className="nav-list">
            {history.map((item) => (
              <button key={item.id} className={"nav-item history-item" + (props.activeId === item.id ? " active" : "")} aria-current={props.activeId === item.id ? "page" : undefined} onClick={() => props.onConversation(item.id)}>
                <ChatTextIcon size={21} aria-hidden="true" /><span>{item.title}</span>
              </button>
            ))}
            {!history.length && <p className="empty-history">从一次新的提问开始</p>}
          </div>
        </section>
      </nav>
      <AccountNavigation />
      <div className="sidebar-foot"><span className="demo-dot" />对话仅本次保留</div>
    </aside>
  );
}
