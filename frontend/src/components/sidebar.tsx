"use client";

import { BookOpenTextIcon, ChartDonutIcon, DatabaseIcon, FileCodeIcon, FlaskIcon, GaugeIcon, RobotIcon, SidebarSimpleIcon, XIcon } from "@phosphor-icons/react";
import { AccountNavigation } from "./authenticated";
import { libraries } from "@/lib/demo-data";
import type { DataCenterTarget } from "@/lib/types";

export type WorkspaceModule = { id: string; label: string };

const testModules = [
  { id: "test-execution", label: "测试执行", Icon: FlaskIcon },
  { id: "test-plans", label: "测试方案", Icon: FileCodeIcon },
];

const moduleGroups = [
  { label: "智能", items: [{ id: "ai-agent", label: "AI Agent", Icon: RobotIcon }, { id: "token-statistics", label: "Token 统计", Icon: ChartDonutIcon }] },
];

type Props = {
  open: boolean;
  toolsOpen: boolean;
  dataCenterOpen: boolean;
  activeModule: string | null;
  onLibrary: (id: string) => void;
  onDataCenter: (target?: DataCenterTarget) => void;
  onModule: (module: WorkspaceModule) => void;
  onClose: () => void;
  onCollapse: () => void;
};

export function Sidebar(props: Props) {
  const operationsOpen = props.activeModule === "operations";
  return (
    <aside className={"sidebar" + (props.open ? " drawer-open" : "")} aria-label="主导航">
      <div className="brand">
        <BookOpenTextIcon size={34} weight="fill" aria-hidden="true" />
        <span>本草知问</span>
        <button className="icon-button desktop-sidebar-toggle" aria-label="收起侧栏" onClick={props.onCollapse}><SidebarSimpleIcon size={22} /></button>
        <button className="icon-button sidebar-close" aria-label="关闭导航" onClick={props.onClose}><XIcon size={21} /></button>
      </div>
      <nav className="sidebar-navigation" aria-label="功能导航">
          <div className="nav-list">
            {libraries.map((library) => (
              <button key={library.id} className={"nav-item" + (props.toolsOpen ? " active" : "")} aria-expanded={props.toolsOpen} aria-haspopup="dialog" onClick={() => props.onLibrary(library.id)}>
                <BookOpenTextIcon size={22} aria-hidden="true" /><span>中药基础资料</span>
              </button>
            ))}
            <button className={"nav-item" + (props.dataCenterOpen ? " active" : "")} aria-haspopup="dialog" aria-expanded={props.dataCenterOpen} onClick={() => props.onDataCenter()}>
              <DatabaseIcon size={22} aria-hidden="true" /><span>数据中心</span>
            </button>
            <button className={"nav-item" + (operationsOpen ? " active" : "")} aria-current={operationsOpen ? "page" : undefined} aria-controls="main-content" onClick={() => props.onModule({ id: "operations", label: "运行总览" })}>
              <GaugeIcon size={22} aria-hidden="true" /><span>运行总览</span>
            </button>
            {testModules.map(({ id, label, Icon }) => (
              <button key={id} className={"nav-item" + (props.activeModule === id ? " active" : "")} aria-haspopup="dialog" aria-expanded={props.activeModule === id} onClick={() => props.onModule({ id, label })}>
                <Icon size={22} aria-hidden="true" /><span>{label}</span>
              </button>
            ))}
          </div>
        {moduleGroups.map((group) => (
          <section className="sidebar-module-group" key={group.label} aria-labelledby={`nav-group-${group.items[0].id}`}>
            <h2 className="nav-label" id={`nav-group-${group.items[0].id}`}>{group.label}</h2>
            <div className="nav-list">
              {group.items.map(({ id, label, Icon }) => (
                <button key={id} className={"nav-item" + (props.activeModule === id ? " active" : "")} aria-current={id === "ai-agent" && props.activeModule === id ? "page" : undefined} aria-controls={id === "ai-agent" ? "main-content" : undefined} aria-haspopup={id === "ai-agent" ? undefined : "dialog"} aria-expanded={id === "ai-agent" ? undefined : props.activeModule === id} onClick={() => props.onModule({ id, label })}>
                  <Icon size={22} aria-hidden="true" /><span>{label}</span>
                </button>
              ))}
            </div>
          </section>
        ))}
      </nav>
      <AccountNavigation />
    </aside>
  );
}
