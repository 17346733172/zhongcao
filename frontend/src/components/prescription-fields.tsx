"use client";
import { PlusCircleIcon, XIcon } from "@phosphor-icons/react";
import { blankMedicine, doseScopeLabels, withDoseScope, type DoseScope, type Medicine, type Prescription } from "@/lib/prescription-api";

export function PrescriptionDoseScope({ value, disabled, onChange }: { value: Prescription; disabled: boolean; onChange: (value: Prescription) => void }) {
  return <label className="rx-label rx-case-scope">本方剂量口径<select aria-label="本方剂量口径" disabled={disabled} value={value.dose_scope ?? "per_dose"} onChange={event => onChange(withDoseScope(value, event.target.value as DoseScope))}>
    <option value="per_dose">每一剂的量</option><option value="total">多剂合计总量</option><option value="unknown">逐味设置 / 尚未确认</option>
  </select><span className="rx-help">按你的要求默认每剂量。如原文为多剂总量或各味口径不同，请调整此项；药量数字保持原值。</span></label>;
}

export function PrescriptionFields({ value, disabled, onChange }: { value: Prescription; disabled: boolean; onChange: (value: Prescription) => void }) {
  function medicine(index: number, patch: Partial<Medicine>) {
    onChange({ ...value, dose_scope: patch.dose_scope && patch.dose_scope !== value.dose_scope ? "unknown" : value.dose_scope, medicines: value.medicines.map((item, i) => i === index ? { ...item, ...patch } : item) });
  }
  return <fieldset className="rx-fields" disabled={disabled}>
    <legend>核对处方数据</legend>
    <p className="rx-help">缺失信息请保持空白或未知；不要根据常识补成「无过敏」或默认克数。可修改识别错误。</p>
    <div className="rx-meta-grid">
      <label>年龄（岁）<input type="number" min={0} max={130} step="any" data-field="age" value={value.age ?? ""} onChange={event => onChange({ ...value, age: event.target.value === "" ? null : Number(event.target.value) })} /></label>
      <label>性别<select data-field="sex" value={value.sex} onChange={event => onChange({ ...value, sex: event.target.value as Prescription["sex"] })}><option value="unknown">未知</option><option value="male">男</option><option value="female">女</option></select></label>
      <label>妊娠状态<select data-field="pregnancy" value={value.pregnancy} onChange={event => onChange({ ...value, pregnancy: event.target.value as Prescription["pregnancy"] })}><option value="unknown">未提供</option><option value="no">已确认非妊娠 / 不适用</option><option value="yes">妊娠</option></select></label>
      <label>总剂数<input type="number" min={1} max={365} step={1} data-field="doses" value={value.doses ?? ""} onChange={event => onChange({ ...value, doses: event.target.value === "" ? null : Number(event.target.value) })} /></label>
      <label>诊断 / 证候<input maxLength={500} data-field="diagnosis" value={value.diagnosis} onChange={event => onChange({ ...value, diagnosis: event.target.value })} /></label>
      <label>过敏史<input maxLength={500} data-field="allergies" value={value.allergies} placeholder="未提供请留空" onChange={event => onChange({ ...value, allergies: event.target.value })} /></label>
      <label className="rx-wide">用法用量<input maxLength={500} data-field="regimen" value={value.regimen} placeholder="照原文填写每日剂数、服法等" onChange={event => onChange({ ...value, regimen: event.target.value })} /></label>
    </div>
    <PrescriptionDoseScope value={value} disabled={disabled} onChange={onChange} />
    <div className="rx-table-scroll" tabIndex={0} aria-label="可横向滚动的处方药物表">
      <table><thead><tr><th>药名 / 炮制品</th><th>剂量数字</th><th>单位</th><th>剂量口径</th><th>煎法 / 用法</th><th>原文</th><th>操作</th></tr></thead><tbody>
        {value.medicines.map((item, index) => <tr key={index}>
          <td><input data-field={`medicines.${index}.name`} aria-label={`第${index + 1}味药名`} maxLength={60} value={item.name} onChange={event => medicine(index, { name: event.target.value })} /></td>
          <td><input data-field={`medicines.${index}.dose`} aria-label={`第${index + 1}味剂量`} inputMode="decimal" maxLength={32} value={item.dose} onChange={event => medicine(index, { dose: event.target.value })} /></td>
          <td><input data-field={`medicines.${index}.unit`} aria-label={`第${index + 1}味单位`} maxLength={12} value={item.unit} onChange={event => medicine(index, { unit: event.target.value })} /></td>
          <td><select data-field={`medicines.${index}.dose_scope`} aria-label={`第${index + 1}味剂量口径`} value={item.dose_scope} onChange={event => medicine(index, { dose_scope: event.target.value as Medicine["dose_scope"] })}>{Object.entries(doseScopeLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></td>
          <td><input aria-label={`第${index + 1}味煎法`} maxLength={150} value={item.method} onChange={event => medicine(index, { method: event.target.value })} /></td>
          <td>{item.source ? <details><summary>核对</summary><p>{item.source}</p></details> : <span>手动录入</span>}</td>
          <td><button type="button" className="icon-button" aria-label={`移除第${index + 1}味药`} onClick={() => onChange({ ...value, medicines: value.medicines.filter((_, i) => i !== index) })}><XIcon size={18} /></button></td>
        </tr>)}
      </tbody></table>
    </div>
    <button type="button" className="quiet-button" disabled={value.medicines.length >= 100} onClick={() => onChange({ ...value, medicines: [...value.medicines, blankMedicine(value.dose_scope ?? "per_dose")] })}><PlusCircleIcon size={19} />添加一味药</button>
  </fieldset>;
}
