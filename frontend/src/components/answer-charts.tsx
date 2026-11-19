"use client";

import { ChartBarIcon } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState } from "react";
import type { AnswerChart } from "@/lib/types";

const colors = ["#215a9e", "#1196aa", "#ca7a1b", "#7272a5"];

export function validAnswerChart(chart: AnswerChart) {
  return chart && typeof chart.title === "string" && Array.isArray(chart.categories) && chart.categories.length > 0
    && chart.categories.length <= 50 && chart.categories.every(label => typeof label === "string")
    && Array.isArray(chart.series) && chart.series.length > 0 && chart.series.length <= 4
    && chart.series.every(series => typeof series.name === "string" && Array.isArray(series.values)
      && series.values.length === chart.categories.length && series.values.every(value => Number.isFinite(value) && value >= 0));
}

function BarChart({ chart }: { chart: AnswerChart }) {
  const titleId = useId();
  const descriptionId = useId();
  const scroll = useRef<HTMLDivElement>(null);
  const [availableWidth, setAvailableWidth] = useState(0);
  useEffect(() => {
    if (!scroll.current) return;
    const observer = new ResizeObserver(entries => setAvailableWidth(Math.floor(entries[0].contentRect.width)));
    observer.observe(scroll.current);
    return () => observer.disconnect();
  }, []);
  const maximum = Math.max(1, ...chart.series.flatMap(series => series.values));
  const step = maximum <= 5 ? 1 : 10 ** Math.floor(Math.log10(maximum / 4));
  const top = Math.ceil(maximum / step) * step;
  const width = Math.max(620, chart.categories.length * 80, availableWidth);
  const left = 48, plotWidth = width - left - 18, plotHeight = 190;
  const groupWidth = plotWidth / chart.categories.length;
  const barWidth = Math.min(30, (groupWidth - 18) / chart.series.length);
  const timestamp = chart.fetchedAt ? new Date(chart.fetchedAt) : null;
  const when = timestamp && !Number.isNaN(timestamp.getTime())
    ? new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(timestamp) : null;
  return <figure className="agent-chart-card" aria-labelledby={titleId}>
    <figcaption id={titleId}><ChartBarIcon size={16} aria-hidden="true" /><span>{chart.title}</span><span className="agent-chart-unit">单位：{chart.unit}</span></figcaption>
    <ul className="agent-chart-legend" aria-label="图例">{chart.series.map((series, index) => <li key={series.name}><span style={{ background: colors[index] }} aria-hidden="true" />{series.name}</li>)}</ul>
    <div ref={scroll} className="agent-chart-scroll" role="region" aria-label={`${chart.title}图表，可横向滚动`} tabIndex={0}>
      <svg width={width} height={260} viewBox={`0 0 ${width} 260`} role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
        <desc id={descriptionId}>{chart.categories.map((category, i) => `${category}：${chart.series.map(series => `${series.name} ${series.values[i]} ${chart.unit}`).join("，")}`).join("；")}</desc>
        {[0, 1, 2, 3, 4].map(index => {
          const y = 14 + plotHeight - index * plotHeight / 4;
          return <g key={index}><line x1={left} x2={width - 18} y1={y} y2={y} stroke="#b8c9db" strokeDasharray="3 4" /><text x={left - 10} y={y + 4} textAnchor="end" className="agent-chart-axis">{Number((index * top / 4).toFixed(2))}</text></g>;
        })}
        {chart.categories.map((category, categoryIndex) => {
          const center = left + groupWidth * (categoryIndex + .5);
          return <g key={`${category}-${categoryIndex}`}>
            {chart.series.map((series, seriesIndex) => {
              const value = series.values[categoryIndex];
              const height = value / top * plotHeight;
              const x = center - barWidth * chart.series.length / 2 + seriesIndex * barWidth;
              return <rect key={series.name} x={x} y={14 + plotHeight - height} width={Math.max(1, barWidth - 3)} height={height} fill={colors[seriesIndex]}><title>{`${category} · ${series.name}：${value} ${chart.unit}`}</title></rect>;
            })}
            <text x={center} y={228} textAnchor="middle" className="agent-chart-category">{category.length > 7 ? category.slice(0, 7) + "…" : category}<title>{category}</title></text>
          </g>;
        })}
      </svg>
    </div>
    <div className="agent-chart-source">{chart.source && <span>来源：{chart.source}</span>}{when && <span>读取时间：{when}（北京时间）</span>}{chart.stale && <span className="agent-chart-stale">上次成功数据，当前状态未确认</span>}</div>
    <details className="agent-chart-data"><summary>查看图表数据</summary><div className="answer-table-scroll"><table><thead><tr><th scope="col">项目</th>{chart.series.map(series => <th scope="col" key={series.name}>{series.name}（{chart.unit}）</th>)}</tr></thead><tbody>{chart.categories.map((category, index) => <tr key={`${category}-${index}`}><th scope="row">{category}</th>{chart.series.map(series => <td key={series.name}>{series.values[index]}</td>)}</tr>)}</tbody></table></div></details>
  </figure>;
}

export function AnswerCharts({ charts }: { charts?: AnswerChart[] }) {
  return <>{charts?.filter(validAnswerChart).slice(0, 3).map((chart, index) => <BarChart key={`${chart.title}-${index}`} chart={chart} />)}</>;
}
