"use client";
import { prescriptionReportText, type ReportItem, type PrescriptionReport as Report } from "@/lib/prescription-api";

function ItemContent({ item }: { item: ReportItem }) {
  return <>{item.lead && <><strong>{item.lead}</strong>{" "}</>}{item.text}
    {!!item.sources.length && <span className="rx-narrative-sources">（{item.sources.map((source, index) => <span key={source.url}>{index > 0 && "、"}<a href={source.url} target="_blank" rel="noreferrer">{source.label}</a></span>)}）</span>}
  </>;
}

export function PrescriptionReport({ report, busy, onSupplement, onFeedback }: { report: Report; busy: boolean; onSupplement: () => void; onFeedback: (text: string) => void }) {
  const sections = report.sections;
  async function copy() {
    try { await navigator.clipboard.writeText(prescriptionReportText(report)); onFeedback("已复制处方检查报告"); }
    catch { onFeedback("无法访问剪贴板，请手动选择报告文字复制。"); }
  }
  return <section className="rx-report" aria-label="处方检查结果">
    <div className="rx-report-tools"><button className="auth-secondary" disabled={busy || sections?.length !== 5} onClick={() => void copy()}>复制报告</button></div>
    {sections?.length === 5 ? sections.map(section => {
      const List = section.ordered ? "ol" : "ul";
      return <section className="rx-narrative-section" key={section.number} aria-labelledby={"rx-section-" + section.number}>
        <h3 id={"rx-section-" + section.number}>{section.number} {section.title}</h3>
        {section.paragraphs.map((item, index) => <p key={index}><ItemContent item={item} /></p>)}
        {!!section.items.length && <List>{section.items.map((item, index) => <li key={index}>
          <ItemContent item={item} />
          {!!item.children.length && <ul>{item.children.map((child, childIndex) => <li key={childIndex}>{child}</li>)}</ul>}
        </li>)}</List>}
        {section.number === "3.1" && !!report.missing_information?.length && <button type="button" className="auth-secondary rx-supplement-action" disabled={busy} onClick={onSupplement}>去补充信息</button>}
      </section>;
    }) : <p className="rx-busy" role="status">正在更新为分节审核报告…</p>}
  </section>;
}
