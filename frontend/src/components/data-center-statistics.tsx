"use client";

import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../lib/api";
import { beijingTime, readStatistics, type StatisticsDays, type StatisticsRange, type StatisticsState, type StatisticsTotals } from "../lib/data-center-api";

const metrics: [keyof StatisticsTotals, string][] = [
  ["prescriptions", "新增处方"], ["batches", "新增批次"], ["completed", "完成批次"],
  ["dispatched_bags", "配发袋数"], ["alarms", "新增报警"],
];
const periods: [StatisticsDays, string][] = [[1, "今天"], [7, "近7天"], [30, "近30天"]];
const beijingDay = (time = Date.now()) => new Date(time + 8 * 3600000).toISOString().slice(0, 10);
const rangeKey = (range: StatisticsRange) => typeof range === "number" ? `days:${range}` : `${range.start_date}:${range.end_date}`;

export function DataCenterStatistics({ refresh }: { refresh: number }) {
  const [range, setRange] = useState<StatisticsRange>(7);
  const [custom, setCustom] = useState(false);
  const [startDate, setStartDate] = useState(() => beijingDay(Date.now() - 6 * 86400000));
  const [endDate, setEndDate] = useState(() => beijingDay());
  const [rangeError, setRangeError] = useState("");
  const [result, setResult] = useState<{ key: string; state: StatisticsState } | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const cache = useRef<Record<string, StatisticsState>>({});
  const key = rangeKey(range);
  const lastRefresh = useRef(refresh);
  const lastRetry = useRef(retry);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let force = lastRefresh.current !== refresh || lastRetry.current !== retry;
    lastRefresh.current = refresh; lastRetry.current = retry;
    setError("");
    async function load() {
      setBusy(true);
      try {
        const state = await readStatistics(range, AbortSignal.any([controller.signal, AbortSignal.timeout(45000)]), force);
        force = false;
        if (!controller.signal.aborted) { cache.current[key] = state; setResult({ key, state }); setError(""); }
      } catch (error) { if (!controller.signal.aborted) setError(errorMessage(error)); }
      finally { if (!controller.signal.aborted) { setBusy(false); timer = setTimeout(load, 60000); } }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [range, key, refresh, retry]);

  const state = result?.key === key ? result.state : cache.current[key];
  const report = state?.data;
  const message = error || state?.error;
  const lastSyncedDay = report ? new Date(Date.parse(report.ended_at) + 8 * 3600000).toISOString().slice(0, 10) : "";
  return <section className="dc-time-statistics" aria-labelledby="dc-statistics-title" aria-busy={busy}>
    <div className="dc-section-heading">
      <h3 id="dc-statistics-title">按时间统计</h3>
      <div className="dc-periods" role="group" aria-label="统计时间范围">{periods.map(([value, label]) =>
        <button key={value} type="button" aria-pressed={!custom && range === value} onClick={() => { setCustom(false); setRangeError(""); setRange(value); }}>{label}</button>,
      )}<button type="button" aria-pressed={custom} onClick={() => {
        if (!custom) { setStartDate(report?.daily[0]?.date ?? startDate); setEndDate(report?.daily.at(-1)?.date ?? endDate); }
        setCustom(true); setRangeError("");
      }}>自定义</button></div>
    </div>
    {custom && <form className="dc-date-range" noValidate onSubmit={event => {
      event.preventDefault();
      const days = (Date.parse(endDate) - Date.parse(startDate)) / 86400000 + 1;
      if (!startDate || !endDate) { setRangeError("请选择开始日期和结束日期。"); return; }
      if (startDate > endDate) { setRangeError("开始日期不能晚于结束日期。"); return; }
      if (endDate > beijingDay()) { setRangeError("结束日期不能晚于今天（北京时间）。"); return; }
      if (!Number.isFinite(days) || days > 366) { setRangeError("一次最多查询366天，请缩小时间范围。"); return; }
      setRangeError(""); setRange({ start_date: startDate, end_date: endDate });
    }}>
      <label>开始日期<input type="date" value={startDate} max={endDate || beijingDay()} required aria-describedby="dc-date-help dc-date-error" onChange={event => { setStartDate(event.target.value); setRangeError(""); }} /></label>
      <label>结束日期<input type="date" value={endDate} min={startDate} max={beijingDay()} required aria-describedby="dc-date-help dc-date-error" onChange={event => { setEndDate(event.target.value); setRangeError(""); }} /></label>
      <button type="submit">查询</button>
      <p id="dc-date-help">包含起止日期，最多366天。修改日期后点击查询。</p>
      <p id="dc-date-error" className="dc-danger" role="alert">{rangeError}</p>
    </form>}
    <p className="dc-statistics-note">按北京时间自然日统计；快捷范围包含今天，自定义范围包含起止两天。</p>
    {message && <div className="dc-error" role="status">{message}{report && " 当前展示上次同步的历史记录。"}<button disabled={busy} onClick={() => setRetry(value => value + 1)}>重试统计</button></div>}
    {!message && state?.stale && <p className="dc-statistics-note" role="status">历史记录尚未更新，当前展示上次同步的统计。</p>}
    {busy && <p className="dc-loading" role="status">{report ? "正在更新历史统计…" : "正在读取历史统计…"}</p>}
    {report && <>
      <p className="dc-statistics-range">统计范围：{report.daily[0]?.date} 至 {report.daily.at(-1)?.date}（北京时间）<br />历史同步时间：{beijingTime(state?.synced_at)}{state?.stale ? " · 数据待更新" : ""}</p>
      {report.earliest_record_at && report.partial && <p className="dc-history-warning">历史记录自 {beijingTime(report.earliest_record_at)} 起留存。本区间仅汇总已留存记录，首日可能不完整；更早日期显示「未留存」。</p>}
      {!report.totals ? <p className="dc-empty">{report.earliest_record_at ? "所选区间暂无已同步的历史记录" : "平台暂无可统计的历史事件"}</p> : <>
        <dl className="dc-metrics dc-period-metrics" aria-label="所选时间范围统计">{metrics.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{report.totals![key]}<small>{key === "dispatched_bags" ? "袋" : key === "alarms" ? "次" : key === "prescriptions" ? "张" : "个"}</small></dd></div>)}</dl>
        <details className="dc-daily-details" key={key}>
          <summary>查看每日明细（{report.days}天）</summary>
          <div className="dc-table-scroll" role="region" aria-label="每日统计明细" tabIndex={0}><table>
            <thead><tr><th>日期（北京）</th>{metrics.map(([key, label]) => <th key={key}>{label}</th>)}<th>记录情况</th></tr></thead>
            <tbody>{[...report.daily].reverse().map(day => <tr key={day.date}><td>{day.date}</td>{metrics.map(([key]) => <td key={key}>{day.totals?.[key] ?? "—"}</td>)}<td>{day.coverage === "missing" ? day.date > lastSyncedDay ? "尚未同步" : "未留存" : day.coverage === "partial" ? "首日部分记录" : "已同步"}</td></tr>)}</tbody>
          </table></div>
        </details>
        {!Object.values(report.totals).some(value => value > 0) && <p className="dc-statistics-note">所选区间内没有新增业务事件。</p>}
      </>}
      <p className="dc-statistics-note">完成批次、配发袋数、新增报警按事件发生日期统计；与下方当前状态、累计数量分别计算。</p>
    </>}
  </section>;
}
