import { AgenticPipelineViz } from "./AgenticPipelineViz";
import "./studioPipeline.css";

// DEV-ONLY harness (gated by ?vizdemo=1 in App.tsx) to iterate the production-graph viz visually
// WITHOUT a real run. Not linked from any UI; safe to leave (only renders when the flag is present).
export function VizDemo() {
  const runningReject = [
    { verdict: "reject", overall_verdict: "reject", accepted: false, revised_layer: "开场 (lead)", note: "lead 偏旁白" },
  ];
  const done = [
    { verdict: "reject", overall_verdict: "reject", accepted: false, revised_layer: "开场 (lead)", note: "" },
    { verdict: "accept", overall_verdict: "accept", accepted: true, revised_layer: null, note: null },
  ];
  return (
    <div style={{ background: "#0e0b08", minHeight: "100vh", padding: 40, fontFamily: "system-ui" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto" }}>
        <h3 style={{ color: "#f5e6d0" }}>① running · mid-loop, reject just fired (creating A)</h3>
        <div className="sc-panel">
          <div className="sc-panel__body">
            <AgenticPipelineViz running={true} rounds={runningReject} currentNode="stage_a" currentRound={2} judgeAvailable />
          </div>
        </div>
        <h3 style={{ color: "#f5e6d0", marginTop: 34 }}>② done · two rounds (round1 reject → round2 accept)</h3>
        <div className="sc-panel">
          <div className="sc-panel__body">
            <AgenticPipelineViz running={false} rounds={done} currentNode="final_report" judgeAvailable />
          </div>
        </div>
      </div>
    </div>
  );
}
