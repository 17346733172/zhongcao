"use client";
import { PlusCircleIcon, XIcon } from "@phosphor-icons/react";
import { useId, useState } from "react";
import { blankMedicine, doseScopeLabels, withDoseScope, type DoseScope, type Medicine, type MissingInformation, type Prescription } from "@/lib/prescription-api";

const missingText = new Set(["", "未知", "未提供", "不详", "未记录", "待补充", "不清楚"]);

export function PrescriptionDoseScope({ value, disabled, onChange }: { value: Prescription; disabled: boolean; onChange: (value: Prescription) => void }) {
  return <label className="rx-label rx-case-scope">本方剂量口径<select aria-label="本方剂量口径" disabled={disabled} value={value.dose_scope ?? "per_dose"} onChange={event => onChange(withDoseScope(value, event.target.value as DoseScope))}>
    <option value="per_dose">每一剂的量</option><option value="total">多剂合计总量</option><option value="unknown">逐味设置 / 尚未确认</option>
  </select><span className="rx-help">按你的要求默认每剂量。如原文为多剂总量或各味口径不同，请调整此项；药量数字保持原值。</span></label>;
}

export function PrescriptionFields({ value, disabled, missingInformation, onChange }: {
  value: Prescription;
  disabled: boolean;
  missingInformation?: MissingInformation[];
  onChange: (value: Prescription) => void;
}) {
  const hintId = useId();
  const [reportedRows, setReportedRows] = useState(() => value.medicines.map((_, index) => index));
  const reportedFields = new Set(missingInformation?.map(item => item.field));

  function field(path: string, missing: boolean, reportedPath = path) {
    const invalid = missing && reportedFields.has(reportedPath);
    return { "data-field": path, "aria-invalid": invalid || undefined, "aria-describedby": invalid ? hintId : undefined };
  }

  function medicineField(index: number, name: "name" | "dose" | "unit" | "dose_scope", missing: boolean) {
    return field(`medicines.${index}.${name}`, missing, `medicines.${reportedRows[index]}.${name}`);
  }

  function medicine(index: number, patch: Partial<Medicine>) {
    onChange({ ...value, dose_scope: patch.dose_scope && patch.dose_scope !== value.dose_scope ? "unknown" : value.dose_scope, medicines: value.medicines.map((item, i) => i === index ? { ...item, ...patch } : item) });
  }

  function removeMedicine(index: number) {
    setReportedRows(rows => rows.filter((_, row) => row !== index));
    onChange({ ...value, medicines: value.medicines.filter((_, row) => row !== index) });
  }

  return <fieldset className="rx-fields" disabled={disabled}>
    <legend>核对处方数据</legend>
    <p className="rx-help">缺失信息请保持空白或未知；不要根据常识补成「无过敏」或默认克数。可修改识别错误。</p>
    {reportedFields.size > 0 && <p className="rx-help" id={hintId}>红框标出报告中仍需补充的项目，请对照原文填写。</p>}
    <div className="rx-meta-grid">
      <label>年龄（岁）<input type="number" min={0} max={130} step="any" {...field("age", value.age === null)} value={value.age ?? ""} onChange={event => onChange({ ...value, age: event.target.value === "" ? null : Number(event.target.value) })} /></label>
      <label>性别<select {...field("sex", value.sex === "unknown")} value={value.sex} onChange={event => onChange({ ...value, sex: event.target.value as Prescription["sex"] })}><option value="unknown">未知</option><option value="male">男</option><option value="female">女</option></select></label>
      <label>妊娠状态<select {...field("pregnancy", value.sex === "female" && value.pregnancy === "unknown")} value={value.pregnancy} onChange={event => onChange({ ...value, pregnancy: event.target.value as Prescription["pregnancy"] })}><option value="unknown">未提供</option><option value="no">已确认非妊娠 / 不适用</option><option value="yes">妊娠</option></select></label>
      <label>总剂数<input type="number" min={1} max={365} step={1} {...field("doses", value.doses === null)} value={value.doses ?? ""} onChange={event => onChange({ ...value, doses: event.target.value === "" ? null : Number(event.target.value) })} /></label>
      <label>诊断 / 证候<input maxLength={500} {...field("diagnosis", missingText.has(value.diagnosis.trim()))} value={value.diagnosis} onChange={event => onChange({ ...value, diagnosis: event.target.value })} /></label>
      <label>过敏史<input maxLength={500} {...field("allergies", missingText.has(value.allergies.trim()))} value={value.allergies} placeholder="未提供请留空" onChange={event => onChange({ ...value, allergies: event.target.value })} /></label>
      <label className="rx-wide">用法用量<input maxLength={500} {...field("regimen", missingText.has(value.regimen.trim()))} value={value.regimen} placeholder="照原文填写每日剂数、服法等" onChange={event => onChange({ ...value, regimen: event.target.value })} /></label>
    </div>
    <PrescriptionDoseScope value={value} disabled={disabled} onChange={onChange} />
    <div className="rx-table-scroll" tabIndex={0} aria-label="可横向滚动的处方药物表">
      <table><thead><tr><th>药名 / 炮制品</th><th>剂量数字</th><th>单位</th><th>剂量口径</th><th>煎法 / 用法</th><th>原文</th><th>操作</th></tr></thead><tbody>
        {value.medicines.map((item, index) => <tr key={index}>
          <td><input {...medicineField(index, "name", !item.name.trim())} aria-label={`第${index + 1}味药名`} maxLength={60} value={item.name} onChange={event => medicine(index, { name: event.target.value })} /></td>
          <td><input {...medicineField(index, "dose", !item.dose.trim())} aria-label={`第${index + 1}味剂量`} inputMode="decimal" maxLength={32} value={item.dose} onChange={event => medicine(index, { dose: event.target.value })} /></td>
          <td><input {...medicineField(index, "unit", !item.unit.trim())} aria-label={`第${index + 1}味单位`} maxLength={12} value={item.unit} onChange={event => medicine(index, { unit: event.target.value })} /></td>
          <td><select {...medicineField(index, "dose_scope", item.dose_scope === "unknown")} aria-label={`第${index + 1}味剂量口径`} value={item.dose_scope} onChange={event => medicine(index, { dose_scope: event.target.value as Medicine["dose_scope"] })}>{Object.entries(doseScopeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></td>
          <td><input data-field={`medicines.${index}.method`} aria-label={`第${index + 1}味煎法`} maxLength={150} value={item.method} onChange={event => medicine(index, { method: event.target.value })} /></td>
          <td>{item.source ? <details><summary>核对</summary><p>{item.source}</p></details> : <span>手动录入</span>}</td>
          <td><button type="button" className="icon-button" aria-label={`移除第${index + 1}味药`} onClick={() => removeMedicine(index)}><XIcon size={18} /></button></td>
        </tr>)}
      </tbody></table>
    </div>
    <button type="button" className="quiet-button" disabled={value.medicines.length >= 100} onClick={() => onChange({ ...value, medicines: [...value.medicines, blankMedicine(value.dose_scope ?? "per_dose")] })}><PlusCircleIcon size={19} />添加一味药</button>
  </fieldset>;
}
