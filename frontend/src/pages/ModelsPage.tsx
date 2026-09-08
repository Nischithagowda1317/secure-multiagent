import { useEffect, useState } from "react";
import { get } from "../api";
import JsonData from "../components/JsonData";
import { Badge, ErrorBox, Loading, Panel } from "../components/UI";

interface ModelStatus { model_name: string; artifact_path: string; available: boolean; metrics: Record<string, unknown>; trained_at?: string }
export default function ModelsPage() {
  const [models, setModels] = useState<ModelStatus[]>([]); const [error, setError] = useState("");
  useEffect(() => { get<ModelStatus[]>("/models").then(setModels).catch((err: Error) => setError(err.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!models.length) return <Loading label="Loading model registry" />;
  return <div className="page-stack"><div className="page-title"><div><span className="eyebrow">Stored model artifacts</span><h1>Model center</h1><p>Training metrics and artifact locations for routing, workload, task risk, sales approval, HITL, agent performance, secure RAG, and the optional neural model.</p></div></div><div className="model-grid">{models.map((model) => <Panel key={model.model_name} title={model.model_name.replace(/_/g, " ")} subtitle={model.artifact_path} actions={<Badge tone={model.available ? "good" : "warn"}>{model.available ? "Available" : "Not trained"}</Badge>}><div className="model-meta"><span>Trained</span><strong>{model.trained_at ? new Date(model.trained_at).toLocaleString() : "Not available"}</strong></div><JsonData value={model.metrics} /></Panel>)}</div></div>;
}
