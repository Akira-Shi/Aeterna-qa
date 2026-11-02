import { useEffect, useRef, useState } from "react";
import { ApiError, approve, artifactHref, getArtifacts, suggest } from "../api";
import type { Artifacts, Decision, Preview, Step, Suggest } from "../api";
import type { Session } from "../App";
import { Errors } from "./Upload";

const nice = (s: string) => s.replace(/_/g, " ").replace("onehot", "one-hot").replace("yeo johnson", "Yeo-Johnson");
const STAGE_TITLE: Record<string, string> = {
  imputation: "Fill missing values", encoding: "Encode categories", scaling: "Scale numbers", imbalance: "Handle class imbalance",
};
const FILE_LABEL: Record<string, string> = {
  "cleaned.csv": "Cleaned CSV",
  "pipeline.joblib": "Fitted pipeline (joblib)",
  "audit.json": "Audit log (JSON)",
  "report.html": "Report (HTML)",
  "cleaning_recipe.json": "Cleaning recipe (JSON)",
};
const ORDER = ["cleaned.csv", "pipeline.joblib", "audit.json", "report.html", "cleaning_recipe.json"];

type Choice = { action: "accept" | "edit"; method: string };

function StepCard({ s, c, onChange, disabled }: { s: Step; c: Choice; onChange: (c: Choice) => void; disabled: boolean }) {
  const name = `step-${s.index}`;
  return (
    <li className="step-card">
      <h3>{STAGE_TITLE[s.stage] ?? s.stage}</h3>
      {s.columns.length > 0 && (
        <div className="cols" aria-label="Columns">{s.columns.map((col) => <span key={col}>{col}</span>)}</div>
      )}
      <p className="method">Suggested: <b>{nice(s.method)}</b> <span className="rule">(rule {s.rule_id})</span></p>
      <p>{s.reason}</p>
      <p className="alt">Alternative: {s.alternative}</p>
      <div className="decide">
        <fieldset disabled={disabled || !s.editable}>
          <legend className="sr">Decision for {STAGE_TITLE[s.stage] ?? s.stage}</legend>
          <label className="seg">
            <input type="radio" name={name} checked={c.action === "accept"} onChange={() => onChange({ action: "accept", method: s.method })} />
            <span>Accept</span>
          </label>
          <label className="seg">
            <input type="radio" name={name} checked={c.action === "edit"}
              onChange={() => onChange({ action: "edit", method: s.allowed_methods.find((m) => m !== s.method) ?? s.method })} />
            <span>Edit</span>
          </label>
        </fieldset>
        {c.action === "edit" && s.editable && (
          <>
            <label className="sr" htmlFor={`${name}-m`}>Method for {STAGE_TITLE[s.stage] ?? s.stage}</label>
            <select id={`${name}-m`} value={c.method} disabled={disabled} onChange={(e) => onChange({ action: "edit", method: e.target.value })}>
              {s.allowed_methods.map((m) => <option key={m} value={m}>{nice(m)}{m === s.method ? " (suggested)" : ""}</option>)}
            </select>
          </>
        )}
        {!s.editable && <span className="help" style={{ margin: 0 }}>Set by your model family; not editable here.</span>}
      </div>
    </li>
  );
}

function PreviewTable({ p }: { p: Preview }) {
  const changedAny = p.n_changed_rows_total > 0;
  return (
    <>
      <p className="help" style={{ margin: "0 0 12px" }}>
        {changedAny
          ? `${p.n_changed_rows_total} row${p.n_changed_rows_total === 1 ? "" : "s"} changed in total; changed rows come first. Changed cells show the value before, struck through.`
          : "No cells changed, so before and after are identical."}
        {p.rows_dropped > 0 && ` ${p.rows_dropped} rows were dropped.`}
      </p>
      <div className="tablewrap" role="region" aria-label="Before and after preview, scrollable" tabIndex={0}>
        <table className="preview">
          <thead>
            <tr><th className="rl" scope="col">Row</th>{p.columns.map((c) => <th key={c} scope="col">{c}</th>)}</tr>
          </thead>
          <tbody>
            {p.after.map((row, i) => (
              <tr key={i}>
                <th className="rl" scope="row">{p.row_labels[i]}</th>
                {p.columns.map((c) => {
                  const a = row[c], b = p.before[i]?.[c];
                  const changed = String(a ?? "") !== String(b ?? "");
                  return (
                    <td key={c} className={changed ? "chg" : undefined}>
                      {changed && <s>{String(b ?? "empty")}</s>}
                      {String(a ?? "")}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function Stage2({ session, suggestion, setSuggestion, onBack }: {
  session: Session; suggestion: Suggest | null; setSuggestion: (s: Suggest) => void; onBack: () => void;
}) {
  const [loading, setLoading] = useState(!suggestion);
  const [err, setErr] = useState<string[]>([]);
  const [choices, setChoices] = useState<Record<number, Choice>>({});
  const [approving, setApproving] = useState(false);
  const [arts, setArts] = useState<Artifacts | null>(null);
  const asked = useRef(false);
  const doneRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (suggestion || asked.current) return;
    asked.current = true;
    suggest(session.jobId)
      .then(setSuggestion)
      .catch((e) => setErr(e instanceof ApiError ? e.messages : ["Could not get suggestions."]))
      .finally(() => setLoading(false));
  }, [session.jobId, suggestion, setSuggestion]);

  const choiceFor = (s: Step): Choice => choices[s.index] ?? { action: "accept", method: s.method };

  const doApprove = async () => {
    if (!suggestion) return;
    setErr([]);
    setApproving(true);
    const decisions: Decision[] = suggestion.steps.flatMap((s) => {
      const c = choiceFor(s);
      return c.action === "edit" && c.method !== s.method ? [{ step: s.index, action: "edit" as const, method: c.method }] : [];
    });
    try {
      await approve(session.jobId, decisions);
      setArts(await getArtifacts(session.jobId));
      setTimeout(() => doneRef.current?.focus(), 50);
    } catch (e) {
      setErr(e instanceof ApiError ? e.messages : ["Could not approve the pipeline."]);
    } finally {
      setApproving(false);
    }
  };

  const files = arts ? [...arts.files].sort((a, b) => ORDER.indexOf(a.name) - ORDER.indexOf(b.name)) : [];

  return (
    <div className="page">
      <h1>Prepare the data for your model</h1>
      <p className="lede">Each step below comes from a rule, with the reason shown. Accept it or switch to another method. Nothing is fitted until you approve.</p>

      <Errors items={err} title="Something went wrong" />

      {loading && (
        <div className="spinner" role="status" style={{ marginBottom: 32 }}><i /> Working out suggestions. This can take a minute while the choices are compared.</div>
      )}

      {suggestion && (
        <>
          {suggestion.fallback && (
            <div className="notice" role="note">
              <b>Fallback applied.</b> {suggestion.fallback_note ?? "The suggested steps did not beat the default pipeline, so the default is used unless you edit a step."}
            </div>
          )}
          {suggestion.compare_note && <div className="notice">{suggestion.compare_note}</div>}

          <ul className="repairs" aria-label="Pipeline steps">
            {suggestion.steps.map((s) => (
              <StepCard key={s.index} s={s} c={choiceFor(s)} disabled={approving || arts !== null}
                onChange={(c) => setChoices((o) => ({ ...o, [s.index]: c }))} />
            ))}
          </ul>

          {!arts && (
            <div className="actions" style={{ marginTop: 32 }}>
              <button className="btn primary" onClick={doApprove} disabled={approving}>
                {approving ? "Fitting the pipeline" : "Approve and build pipeline"}
              </button>
              <button className="btn" onClick={onBack} disabled={approving}>Back to repairs</button>
            </div>
          )}
          {approving && <div className="spinner" role="status" style={{ marginTop: 16 }}><i /> Fitting on your full upload</div>}
        </>
      )}

      {arts && (
        <section aria-labelledby="dl-h" style={{ marginTop: 56 }}>
          <div className="lead"><h2 id="dl-h" ref={doneRef} tabIndex={-1}>Your pipeline is ready.</h2></div>
          <div className="notice"><b>Refit note.</b> {arts.note}</div>
          <h2 className="serif" style={{ margin: "32px 0 16px" }}>Downloads</h2>
          <div className="dl">
            {files.map((f) => (
              <a key={f.name} className={`btn${f.available ? "" : " na"}`} href={f.available ? artifactHref(f) : undefined}
                download={f.name} aria-disabled={!f.available}>
                {FILE_LABEL[f.name] ?? f.name}
              </a>
            ))}
          </div>
          <h2 className="serif" style={{ margin: "40px 0 16px" }}>Before and after, first 20 rows</h2>
          <PreviewTable p={arts.preview} />
        </section>
      )}
    </div>
  );
}
