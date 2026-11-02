import type { Session } from "../App";

export default function Repairs(_p: { session: Session; onDone: () => void; onNext: () => void; onRerun: (s: Session) => void }) {
  return <div className="page"><h1>Repairs</h1></div>;
}
