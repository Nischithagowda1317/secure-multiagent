import { useEffect, useState } from "react";
import { get } from "../api";
import { BarList, ErrorBox, Loading, Panel, StatCard, formatMoney } from "../components/UI";

interface Overview {
  company: string;
  snapshot_date: string;
  dataset_counts: Record<string, number>;
  projects: { total: number; at_risk: number; high_risk: number };
  sales: { orders: number; sales_usd: number; profit_usd: number };
  approvals: { pending_source: number; pending_runtime: number };
  workflows: Record<string, number>;
  workforce?: { employees: number; overloaded: number; high_or_overloaded: number };
}

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { get<Overview>("/dashboard/overview").then(setData).catch((err: Error) => setError(err.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading label="Loading enterprise overview" />;
  const workflowRows = Object.entries(data.workflows).map(([status, count]) => ({ status, count }));
  return (
    <div className="page-stack">
      <div className="page-title"><div><span className="eyebrow">Dataset snapshot {data.snapshot_date}</span><h1>Enterprise overview</h1><p>Operational, security, AI-quality, and workflow indicators for {data.company}.</p></div></div>
      <div className="stat-grid five">
        <StatCard label="Projects" value={data.projects.total} helper={`${data.projects.at_risk} at risk`} tone={data.projects.at_risk ? "warn" : "good"} />
        <StatCard label="Sales Orders" value={data.sales.orders.toLocaleString()} helper={formatMoney(data.sales.sales_usd)} />
        <StatCard label="Total Profit" value={formatMoney(data.sales.profit_usd)} helper="Curated sales dataset" tone="good" />
        <StatCard label="Pending Approvals" value={data.approvals.pending_source + data.approvals.pending_runtime} helper="Dataset and live requests" tone="warn" />
        <StatCard label="Knowledge Chunks" value={data.dataset_counts.rag_chunks} helper={`${data.dataset_counts.document_catalog} documents`} />
      </div>
      <div className="two-column">
        <Panel title="Workflow outcomes" subtitle="Historical multi-agent run status distribution">
          <BarList items={workflowRows} valueKey="count" labelKey="status" />
        </Panel>
        <Panel title="Implementation coverage" subtitle="Data volume available to the specialist agents">
          <div className="coverage-grid">
            {Object.entries(data.dataset_counts).map(([label, value]) => <div key={label}><span>{label.replace(/_/g, " ")}</span><strong>{value.toLocaleString()}</strong></div>)}
          </div>
        </Panel>
      </div>
      <div className="two-column">
        <Panel title="Project health" subtitle="Current portfolio indicators">
          <div className="mini-stat-row"><div><span>Total projects</span><strong>{data.projects.total}</strong></div><div><span>At risk</span><strong>{data.projects.at_risk}</strong></div><div><span>High risk</span><strong>{data.projects.high_risk}</strong></div></div>
        </Panel>
        <Panel title="Workforce capacity" subtitle={data.workforce ? "Available under your role" : "Restricted by your role"}>
          {data.workforce ? <div className="mini-stat-row"><div><span>Employees</span><strong>{data.workforce.employees}</strong></div><div><span>High workload</span><strong>{data.workforce.high_or_overloaded}</strong></div><div><span>Overloaded</span><strong>{data.workforce.overloaded}</strong></div></div> : <p className="muted">Your assigned role does not have employee.read. Use an HR Manager, Executive, Auditor, AI Reviewer, or Admin account to view workforce indicators.</p>}
        </Panel>
      </div>
    </div>
  );
}
