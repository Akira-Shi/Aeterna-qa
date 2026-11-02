import type { Suggest } from "../api";
import type { Session } from "../App";

export default function Stage2(_p: { session: Session; suggestion: Suggest | null; setSuggestion: (s: Suggest) => void; onBack: () => void }) {
  return <div className="page"><h1>Pipeline</h1></div>;
}
