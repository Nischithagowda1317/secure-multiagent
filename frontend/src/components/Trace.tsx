import type { AgentTrace } from "../types";
import { Badge } from "./UI";

export default function Trace({ agents }: { agents: AgentTrace[] }) {
  return (
    <div className="trace">
      {agents.map((agent, index) => (
        <div className="trace-row" key={`${agent.agent_id}-${index}`}>
          <div className="trace-node">{agent.agent_id}</div>
          <div className="trace-line" />
          <div className="trace-card">
            <div><strong>{agent.agent_name}</strong><Badge tone="good">{agent.status}</Badge></div>
            <p>{agent.summary}</p>
            <small>{agent.duration_ms} ms · Confidence {(agent.confidence * 100).toFixed(0)}%</small>
          </div>
        </div>
      ))}
    </div>
  );
}
