import { DatabaseIcon, RobotIcon, TerminalWindowIcon } from "@phosphor-icons/react";
import type { Answer } from "@/lib/types";

function duration(milliseconds?: number) {
  if (typeof milliseconds !== "number" || !Number.isFinite(milliseconds) || milliseconds < 0) return "";
  return milliseconds >= 1000 ? `${(milliseconds / 1000).toFixed(1)} s` : `${Math.round(milliseconds)} ms`;
}

export function AnswerHeader({ answer, time, answeredAt }: { answer: Answer; time: string; answeredAt?: string }) {
  const timestamp = answeredAt ? new Date(answeredAt) : null;
  const validTime = timestamp && !Number.isNaN(timestamp.getTime());
  const displayedTime = validTime
    ? new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(timestamp)
    : time.replace(/^今天\s*/, "");
  const calls = answer.toolCalls ?? [];
  const usage = answer.usage;
  const validUsage = usage && [usage.inputTokens, usage.outputTokens].every(value => Number.isSafeInteger(value) && value >= 0);
  return <>
    <header className="agent-answer-header">
      <span className="agent-avatar" aria-hidden="true"><RobotIcon size={21} /></span>
      <div className="agent-answer-meta"><span className="agent-name">Agent</span>{displayedTime && <time className="agent-answer-time" dateTime={validTime ? answeredAt : undefined} title="北京时间">{displayedTime}</time>}</div>
      {validUsage && <span className="agent-token-usage" aria-label="工具选择Token用量" title="本轮模型工具选择的实际用量，不含知识库回答生成">{usage.scope === "tool_selection" && <span>工具选择 </span>}{usage.inputTokens.toLocaleString("zh-CN")} 入 / {usage.outputTokens.toLocaleString("zh-CN")} 出</span>}
    </header>
    {calls.length > 0 && <ol className="agent-tool-log" aria-label="工具调用记录">{calls.map((call, index) => {
      const Icon = ["data_center", "herbal_reference"].includes(call.name) ? DatabaseIcon : TerminalWindowIcon;
      return <li className="agent-tool-row" key={`${call.name}-${index}`}>
        <Icon size={15} aria-hidden="true" />
        <span className="agent-tool-name">{call.title}</span>
        <code className="agent-tool-command">MCP · {call.name}.{call.action}</code>
        {call.summary && <span className={"agent-tool-result" + (call.status === "error" ? " agent-tool-error" : call.stale ? " agent-tool-stale" : "")}>{call.summary}</span>}
        {duration(call.durationMs) && <span className="agent-tool-duration">{duration(call.durationMs)}</span>}
      </li>;
    })}</ol>}
  </>;
}
