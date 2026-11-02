import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, startStage1, uploadDataset } from "../api";
import type { Dataset, TaskBody } from "../api";
import { distinctValues, readText } from "../csv";
import type { Session } from "../App";

const FAMILIES: { value: TaskBody["model_family"]; label: string; hint: string }[] = [
  { value: "linear", label: "Linear (logistic or linear regression)", hint: "Needs scaled numbers and unordered categories." },
  { value: "tree_ensemble", label: "Tree ensemble (random forest, boosting)", hint: "Copes with raw scales and missing structure." },
  { value: "distance", label: "Distance-based (k-nearest neighbours)", hint: "Sensitive to scale." },
  { value: "neural", label: "Neural network", hint: "Sensitive to scale." },
];
const TASKS: { value: TaskBody["task_type"]; label: string }[] = [
  { value: "binary", label: "Two classes (binary)" },
  { value: "multiclass", label: "Several classes" },
  { value: "regression", label: "A number (regression)" },
];

export function Errors({ items, title }: { items: string[]; title?: string }) {
  if (!items.length) return null;
  return (
    <div className="alert" role="alert">
      <b>{title ?? (items.length === 1 ? "This needs fixing" : "These need fixing")}</b>
      <ul>{items.map((m, i) => <li key={i}>{m}</li>)}</ul>
    </div>
  );
}

function CheckGroup({ legend, help, columns, value, onChange, disabled }: {
  legend: string; help: string; columns: string[]; value: string[]; onChange: (v: string[]) => void; disabled: string[];
}) {
  return (
    <fieldset className="group">
      <legend>{legend}</legend>
      <p className="help">{help}</p>
      <div className="chips">
        {columns.map((c) => (
          <label key={c} className={`chip${value.includes(c) ? " on" : ""}${disabled.includes(c) ? " off" : ""}`}>
            <input
              type="checkbox"
              checked={value.includes(c)}
              disabled={disabled.includes(c)}
              onChange={(e) => onChange(e.target.checked ? [...value, c] : value.filter((x) => x !== c))}
            />
            <span>{c}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function Upload({ onStarted, busy }: { onStarted: (s: Session) => void; busy: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [ds, setDs] = useState<Dataset | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadErr, setUploadErr] = useState<string[]>([]);

  const [target, setTarget] = useState("");
  const [taskType, setTaskType] = useState<TaskBody["task_type"]>("binary");
  const [positive, setPositive] = useState("");
  const [family, setFamily] = useState<TaskBody["model_family"]>("linear");
  const [ids, setIds] = useState<string[]>([]);
  const [drops, setDrops] = useState<string[]>([]);
  const [planner, setPlanner] = useState<"rule" | "groq">("rule");
  const [starting, setStarting] = useState(false);
  const [startErr, setStartErr] = useState<string[]>([]);
  const errRef = useRef<HTMLDivElement>(null);
  const submitting = useRef(false); // handler-level guard against double clicks and Enter repeats

  const cols = ds?.columns.map((c) => c.name) ?? [];
  const labels = useMemo(() => (text && target ? distinctValues(text, target) : { values: [], capped: false }), [text, target]);

  // Starting task type from the target's profile; the user can change it.
  useEffect(() => {
    if (!ds || !target) return;
    const p = ds.columns.find((c) => c.name === target);
    if (!p) return;
    const numeric = /int|float/.test(p.dtype);
    setTaskType(p.distinct === 2 ? "binary" : numeric && p.distinct > 15 ? "regression" : "multiclass");
    setPositive("");
  }, [ds, target]);

  const onFile = async (f: File | null) => {
    setFile(f);
    setDs(null);
    setUploadErr([]);
    setStartErr([]);
    setTarget("");
    setIds([]);
    setDrops([]);
    if (!f) return;
    setUploading(true);
    try {
      const [d, t] = await Promise.all([uploadDataset(f), readText(f)]);
      setDs(d);
      setText(t);
    } catch (e) {
      setUploadErr(e instanceof ApiError ? e.messages : ["Upload failed."]);
    } finally {
      setUploading(false);
    }
  };

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!ds || busy || submitting.current) return;
    submitting.current = true;
    setStartErr([]);
    setStarting(true);
    try {
      const r = await startStage1({
        dataset_id: ds.dataset_id, target, task_type: taskType,
        positive_label: taskType === "binary" && positive !== "" ? positive : null,
        model_family: family, id_columns: ids, drop_columns: drops, planner,
      });
      onStarted({ jobId: r.job_id, warnings: r.warnings, rows: ds.rows });
    } catch (e) {
      setStartErr(e instanceof ApiError ? e.messages : ["Could not start the job."]);
      setStarting(false);
      submitting.current = false;
      setTimeout(() => errRef.current?.focus(), 0);
    }
  };

  return (
    <div className="page">
      <h1>Clean a table, then prepare it for a model</h1>
      <p className="lede">Upload a CSV and say what you want to predict. Each repair is tried on your data and kept only if it measurably helps.</p>

      <section aria-labelledby="up-h" className="block">
        <h2 id="up-h" className="serif">Your data</h2>
        <label className={`drop${file ? " has" : ""}`}>
          <input type="file" accept=".csv,text/csv" onChange={(e) => onFile(e.target.files?.[0] ?? null)} aria-describedby="up-help" />
          <span className="drop-t">{file ? file.name : "Choose a CSV file"}</span>
          <span className="drop-s" id="up-help">
            {uploading ? "Reading the file." : ds ? `${ds.rows.toLocaleString()} rows, ${ds.n_columns} columns` : "Up to 25 MB, with a header row."}
          </span>
        </label>
        {uploading && <div className="spinner" role="status"><i /> Uploading</div>}
        <Errors items={uploadErr} />
      </section>

      {ds && (
        <form onSubmit={submit} noValidate>
          <section aria-labelledby="task-h" className="block">
            <h2 id="task-h" className="serif">What to predict</h2>
            <div className="grid2">
              <div className="field">
                <label htmlFor="target">Target column</label>
                <select id="target" value={target} onChange={(e) => { setTarget(e.target.value); setStartErr([]); }} required>
                  <option value="">Choose a column</option>
                  {cols.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="task">Kind of target</label>
                <select id="task" value={taskType} onChange={(e) => setTaskType(e.target.value as TaskBody["task_type"])} disabled={!target}>
                  {TASKS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
            </div>
            {taskType === "binary" && (
              <div className="field">
                <label htmlFor="pos">Positive label</label>
                <select id="pos" value={positive} onChange={(e) => setPositive(e.target.value)} disabled={!target} aria-describedby="pos-h">
                  <option value="">Choose automatically</option>
                  {labels.values.map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
                <p className="help" id="pos-h">
                  {labels.capped ? "This column has many distinct values, so it may not be a two-class target." : "The outcome you care about finding."}
                </p>
              </div>
            )}
            <div className="field">
              <label htmlFor="fam">Model family you plan to use</label>
              <select id="fam" value={family} onChange={(e) => setFamily(e.target.value as TaskBody["model_family"])} aria-describedby="fam-h">
                {FAMILIES.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
              <p className="help" id="fam-h">{FAMILIES.find((f) => f.value === family)?.hint}</p>
            </div>
          </section>

          <details className="block opt">
            <summary>Leave columns out (optional)</summary>
            <CheckGroup legend="Identifier columns" help="Row ids and keys. They are excluded from modelling."
              columns={cols} value={ids} onChange={setIds} disabled={cols.filter((c) => c === target || drops.includes(c))} />
            <CheckGroup legend="Columns to drop" help="Anything the model should not see."
              columns={cols} value={drops} onChange={setDrops} disabled={cols.filter((c) => c === target || ids.includes(c))} />
          </details>

          <fieldset className="block planner">
            <legend className="serif">Repair planner</legend>
            <label className={`opt-card${planner === "rule" ? " on" : ""}`}>
              <input type="radio" name="planner" checked={planner === "rule"} onChange={() => setPlanner("rule")} />
              <span><b>Rule-based</b><em>Default. Works offline and gives the same plan every time.</em></span>
            </label>
            <label className={`opt-card${planner === "groq" ? " on" : ""}`}>
              <input type="radio" name="planner" checked={planner === "groq"} onChange={() => setPlanner("groq")} />
              <span><b>Groq language model</b><em>Needs a network connection and an API key on this machine.</em></span>
            </label>
          </fieldset>

          <div ref={errRef} tabIndex={-1} className="errwrap"><Errors items={startErr} /></div>
          <div className="actions">
            <button className="btn primary" type="submit" disabled={!target || starting || busy}>
              {starting ? "Starting" : busy ? "A job is in progress" : "Start cleaning"}
            </button>
            {!target && !busy && <span className="help">Choose a target column to continue.</span>}
            {busy && <span className="help">Your current job has to finish, fail or be cancelled before another can start.</span>}
          </div>
        </form>
      )}
    </div>
  );
}
