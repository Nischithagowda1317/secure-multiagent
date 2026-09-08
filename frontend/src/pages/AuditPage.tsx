import { useEffect, useState } from "react";
import { get } from "../api";
import { DataTable, ErrorBox, Loading, Panel } from "../components/UI";

interface AuditData { runtime: Array<Record<string, unknown>>; dataset: Array<Record<string, unknown>> }
export default function AuditPage() {
  const [data, setData] = useState<AuditData | null>(null); const [error, setError] = useState("");
  useEffect(() => { get<AuditData>("/audit?limit=75").then(setData).catch((err: Error) => setError(err.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading label="Loading audit records" />;
  return <div className="page-stack"><div className="page-title"><div><span className="eyebrow">Immutable operational evidence</span><h1>Audit logs</h1><p>Authorization decisions, workflow runs, uploads, human approvals, and historical synthetic audit events.</p></div></div><Panel title="Live application events" subtitle={`${data.runtime.length} recent records`}><DataTable rows={data.runtime} maxRows={75} /></Panel><Panel title="Dataset audit history" subtitle={`${data.dataset.length} recent records`}><DataTable rows={data.dataset} maxRows={75} /></Panel></div>;
}
