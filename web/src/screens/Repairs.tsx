import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getJob, getStage1, rerun } from "../api";
import type { JobStatus, Repair, Stage1 } from "../api";
import type { Session } from "../App";
import { Errors } from "./Upload";

const POLL_MS = 1500;
const STATUS: Record<string, { label: string; cls: string }> = {
  committed: { label: "Committed", cls: "committed" },
  discarded: { label: "Rolled back", cls: "discarded" },
  staged: { label: "Held for a combined test", cls: "other" },
};

const fmt = (n: number | null | undefined, signed = false) =>
  n === null || n === undefined ? "n/a" : `${signed && n > 0 ? "+" : ""}${n.toFixed(4)}`;
// The headline comes from the API and names the scoring rule; the UI keeps that out of view.
const plain = (s: string) => s.replace(/neg-Brier/gi, "score");
const stripTag = (s: string) => s.replace(/^[A-Z_ ]+ - /, "");

function Gauge({ r }: { r: Repair }) {
  const d = r.delta ?? 0, se = r.se ?? 0, bar = r.threshold ?? 0;
  const span = Math.max(Math.abs(d) + se, bar, 1e-6) * 1.25;       // half-width of the track
  const pct = (v: number) => (v / span) * 50;                      // percent of the full track, from centre
  const left = d >= 0 ? 50 : 50 + pct(d);
  return (
    <div className="gauge-row">
      <div className="gauge" role="img"
        aria-label={`Effect ${fmt(d, true)}, plus or minus ${fmt(se)}. Needed to commit: ${fmt(bar)}.`}>
        <span className="zero" />
        <span className="se" style={{ left: `${50 + pct(d - se)}%`, width: `${Math.max(pct(2 * se), 0)}%` }} />
        <span className={`fill ${d > 0 ? "pos" : ""}`} style={{ left: `${left}%`, width: `${Math.abs(pct(d))}%` }} />
        <span className="tick" style={{ left: `calc(${50 + pct(bar)}% - 1px)` }} />
      </div>
      <div className="gauge-cap">
        <span>Effect <b>{fmt(d, true)}</b> &plusmn; {fmt(se)}</span>
        <span>Bar to commit <b>{fmt(bar)}</b></span>
      </div>
    </div>
  );
}

function Card({ r }: { r: Repair }) {
  const st = STATUS[r.status] ?? { label: r.status, cls: "other" };
  return (
    <li className="repair">
      <header>
        <div>
          <h3>{r.plain_fix ?? r.operation ?? "Repair"}</h3>
          {r.column && <p className="col">Column {r.column}</p>}
        </div>
        <span className={`pill ${st.cls}`}>{st.label}</span>
      </header>
      {r.verdict && <p className="verdict">{stripTag(r.verdict.text)}</p>}
      {r.error ? <p className="note">{r.error}</p> : <Gauge r={r} />}
      {r.reason && <p className="note">Why it was tried: {r.reason}</p>}
    </li>
  );
}

export default function Repairs({ session, onDone, onNext, onRerun }: {
  session: Session; onDone: () => void; onNext: () => void; onRerun: (s: Session) => void;
}) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [res, setRes] = useState<Stage1 | null>(null);
  const [err, setErr] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const loaded = useRef(false);

  const fetchResult = useCallback(async () => {
    try {
      setRes(await getStage1(session.jobId));
      onDone();
    } catch (e) {
      setErr(e instanceof ApiError ? e.messages : ["Could not load the results."]);
    }
  }, [session.jobId, onDone]);

  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const j = await getJob(session.jobId);
        if (stop) return;
        setJob(j);
        setErr([]);
        if (j.status === "done") {
          if (!loaded.current) { loaded.current = true; await fetchResult(); }
          return;
        }
        if (j.status === "queued" || j.status === "running") timer = setTimeout(tick, POLL_MS);
      } catch (e) {
        if (stop) return;
        setErr(e instanceof ApiError ? e.messages : ["Lost contact with the API."]);
        timer = setTimeout(tick, POLL_MS * 3);
      }
    };
    tick();
    return () => { stop = true; clearTimeout(timer); };
  }, [session.jobId, fetchResult]);

  const doRerun = async () => {
    setBusy(true);
    try {
      const r = await rerun(session.jobId);
      onRerun({ jobId: r.job_id, warnings: r.warnings });
    } catch (e) {
      setErr(e instanceof ApiError ? e.messages : ["Could not rerun."]);
      setBusy(false);
    }
  };

  const running = !job || job.status === "queued" || job.status === "running";
  const n = job?.progress.iteration ?? 0, of = job?.progress.of ?? 16;

  return (
    <div className="page">
      <h1>Repairs, tried one at a time</h1>
      <p className="lede">Every repair is tested on held-out folds of your data. It is committed only when the gain clears the bar; otherwise it is rolled back.</p>

      {session.warnings.length > 0 && (
        <div className="notice"><b>Heads up.</b> {session.warnings.join(" ")}</div>
      )}
      <Errors items={err} title="Something went wrong" />

      {running && !err.length && (
        <section className="progress" aria-live="polite">
          <h2>{job?.status === "queued" || !job ? "Waiting to start" : `Evaluating repair ${Math.min(n + 1, of)} of ${of}`}</h2>
          <p className="help">{n} of {of} steps finished. This usually takes a minute or two.</p>
          <div className={`bar${n === 0 ? " idle" : ""}`} role="progressbar" aria-valuemin={0} aria-valuemax={of} aria-valuenow={n} aria-label="Repair progress">
            <i style={{ width: `${(n / of) * 100}%` }} />
          </div>
        </section>
      )}

      {job?.status === "planner_unavailable" && (
        <section className="progress">
          <h2>The Groq planner could not be reached</h2>
          <p style={{ margin: "8px 0 20px" }}>{job.message ?? "The language model did not answer."} Nothing was changed in your data.</p>
          <button className="btn primary" onClick={doRerun} disabled={busy}>{busy ? "Starting" : "Rerun with the rule-based planner"}</button>
        </section>
      )}

      {job && (job.status === "failed" || job.status === "interrupted") && (
        <div className="alert" role="alert">
          <b>The job stopped</b>
          <ul><li>{job.message ?? "The API restarted or the run hit an error."}</li></ul>
        </div>
      )}

      {res && res.mode === "gated" && (() => {
        const all = res.repairs ?? [];
        const cards = all.filter((r) => r.column);
        const notes = all.filter((r) => !r.column && r.error).map((r) => r.error as string);
        const kept = cards.filter((r) => r.status === "committed").length;
        const back = cards.filter((r) => r.status === "discarded").length;
        return (
          <>
            <section className="lead">
              <h2>{kept === 0 ? "Nothing cleared the bar, so your data was left as it was." : `${kept} repair${kept === 1 ? "" : "s"} cleared the bar and ${kept === 1 ? "was" : "were"} applied.`}</h2>
              {res.headline && <p>{plain(res.headline).replace(/ -> /g, " to ")}</p>}
            </section>
            <div className="stats">
              <div className="stat"><b>{cards.length}</b><span>tried</span></div>
              <div className="stat"><b>{kept}</b><span>committed</span></div>
              <div className="stat"><b>{back}</b><span>rolled back</span></div>
            </div>
            <ul className="repairs">
              {cards.map((r) => <Card key={r.iteration} r={r} />)}
            </ul>
            {notes.map((m, i) => <p key={i} className="help" style={{ marginTop: 16 }}>{m}</p>)}
          </>
        );
      })()}
      {res && res.mode !== "gated" && (
        <div className="notice"><b>Detection only.</b> This kind of target cannot be gated yet, so the data was scanned but not changed. You can still get a pipeline suggestion.</div>
      )}

      {res && (
        <div className="actions" style={{ marginTop: 32 }}>
          <button className="btn primary" onClick={onNext}>Continue to pipeline</button>
        </div>
      )}
    </div>
  );
}
