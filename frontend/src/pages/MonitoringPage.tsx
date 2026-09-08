import { useEffect, useState } from "react";
import { get } from "../api";
import JsonData from "../components/JsonData";
import { BarList, ErrorBox, Loading, Panel, Progress, StatCard } from "../components/UI";

interface MonitoringData {
  snapshot_date?: string;
  average_pass_rate: number;
  average_review_rate: number;
  average_regression_rate: number;
  average_hallucination_rate: number;
  judge_human_disagreement_rate: number;
  workflow_status_counts: Record<string, number>;
  average_workflow_execution_ms: number;
  average_workflow_confidence: number;
  average_grounding_score: number;
  judge_error_types: Record<string, number>;
}

export default function MonitoringPage() {
  const [data, setData] = useState<MonitoringData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { get<MonitoringData>("/dashboard/monitoring").then(setData).catch((err: Error) => setError(err.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading label="Loading agent reliability metrics" />;
  const statuses = Object.entries(data.workflow_status_counts).map(([status, count]) => ({ status, count }));
  const errors = Object.entries(data.judge_error_types).map(([error_type, count]) => ({ error_type, count }));
  return <div className="page-stack"><div className="page-title"><div><span className="eyebrow">Monitoring Agent snapshot {data.snapshot_date}</span><h1>AI reliability and observability</h1><p>Pass rate, human review, hallucination, grounding, disagreement, latency, cost, and judge-error signals.</p></div></div><div className="stat-grid five"><StatCard label="Pass Rate" value={`${(data.average_pass_rate * 100).toFixed(1)}%`} tone="good" /><StatCard label="Review Rate" value={`${(data.average_review_rate * 100).toFixed(1)}%`} tone="warn" /><StatCard label="Hallucination" value={`${(data.average_hallucination_rate * 100).toFixed(1)}%`} tone={data.average_hallucination_rate > .1 ? "danger" : "good"} /><StatCard label="Average Latency" value={`${data.average_workflow_execution_ms.toFixed(0)} ms`} /><StatCard label="Disagreement" value={`${(data.judge_human_disagreement_rate * 100).toFixed(1)}%`} /></div><div className="two-column"><Panel title="Quality scores"><Progress value={data.average_workflow_confidence * 100} label="Workflow confidence" /><Progress value={data.average_grounding_score * 100} label="Grounding score" /><Progress value={(1 - data.average_regression_rate) * 100} label="Regression-free rate" /></Panel><Panel title="Workflow outcomes"><BarList items={statuses} valueKey="count" labelKey="status" /></Panel></div><div className="two-column"><Panel title="Judge error categories"><BarList items={errors} valueKey="count" labelKey="error_type" /></Panel><Panel title="Raw monitoring summary"><JsonData value={data} /></Panel></div></div>;
}
