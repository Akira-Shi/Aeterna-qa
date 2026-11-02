import { useCallback, useState } from "react";
import type { Suggest } from "./api";
import Upload from "./screens/Upload";
import Repairs from "./screens/Repairs";
import Stage2 from "./screens/Stage2";

type Screen = 1 | 2 | 3;
const STEPS = ["Upload and task", "Repairs", "Pipeline and download"];

export interface Session {
  jobId: string;
  warnings: string[];
  rows: number;
}

export default function App() {
  const [screen, setScreen] = useState<Screen>(1);
  const [session, setSession] = useState<Session | null>(null);
  const [suggestion, setSuggestion] = useState<Suggest | null>(null);
  const [stage1Done, setStage1Done] = useState(false);
  const [jobActive, setJobActive] = useState(false); // a stage 1 job is queued or running

  const start = (s: Session) => {
    setSession(s);
    setSuggestion(null);
    setStage1Done(false);
    setJobActive(true);
    setScreen(2);
  };

  const settled = useCallback(() => setJobActive(false), []);
  const cancelled = () => {
    setSession(null);
    setJobActive(false);
    setScreen(1);
  };

  const markDone = useCallback(() => setStage1Done(true), []);

  const reachable = (n: Screen) => n === 1 || (n === 2 && session !== null) || (n === 3 && stage1Done);

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="top">
        <div className="top-in">
          <span className="mark">AETERNA-QA</span>
          <nav aria-label="Progress">
            <ol className="steps">
              {STEPS.map((label, i) => {
                const n = (i + 1) as Screen;
                const state = n === screen ? "current" : n < screen ? "done" : "todo";
                return (
                  <li key={label} className={`step ${state}`}>
                    <button
                      type="button"
                      onClick={() => setScreen(n)}
                      disabled={!reachable(n) || n === screen}
                      aria-label={`Step ${n}: ${label}`}
                      aria-current={n === screen ? "step" : undefined}
                    >
                      <span className="dot" aria-hidden="true">{n}</span>
                      <span className="lbl">{label}</span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {screen === 1 && <Upload onStarted={start} busy={jobActive} />}
        {screen === 2 && session && (
          <Repairs key={session.jobId} session={session} onDone={markDone} onSettled={settled} onCancelled={cancelled} onNext={() => setScreen(3)} onRerun={start} />
        )}
        {screen === 3 && session && (
          <Stage2 key={session.jobId} session={session} suggestion={suggestion} setSuggestion={setSuggestion} onBack={() => setScreen(2)} />
        )}
      </main>
    </>
  );
}
