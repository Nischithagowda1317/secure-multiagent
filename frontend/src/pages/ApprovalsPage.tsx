import { useEffect, useState } from "react";
import { get, post } from "../api";
import JsonData from "../components/JsonData";
import { Badge, Empty, ErrorBox, Loading, Panel } from "../components/UI";

interface ApprovalData { runtime: Array<Record<string, unknown>>; dataset_pending: Array<Record<string, unknown>> }

export default function ApprovalsPage() {
  const [data, setData] = useState<ApprovalData | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  function refresh() { get<ApprovalData>("/approvals").then(setData).catch((err: Error) => setError(err.message)); }
  useEffect(refresh, []);
  async function decide(id: string, decision: string) {
    setBusy(id); setError("");
    try { await post(`/approvals/${id}/decision`, { decision, comment: `Decision entered from dashboard: ${decision}` }); refresh(); }
    catch (err) { setError(err instanceof Error ? err.message : "Decision failed"); }
    finally { setBusy(""); }
  }
  if (error && !data) return <ErrorBox message={error} />;
  if (!data) return <Loading label="Loading approvals" />;
  const records = [...data.runtime, ...data.dataset_pending];
  return <div className="page-stack"><div className="page-title"><div><span className="eyebrow">Human-in-the-Loop gateway</span><h1>Approval queue</h1><p>User-requested sensitive actions remain paused until an authorized human decides.</p></div></div>{error && <ErrorBox message={error} />}{records.length === 0 ? <Empty message="No approval records are available." /> : <div className="approval-grid">{records.map((record) => { const id = String(record.approval_id ?? ""); const status = String(record.status ?? "Pending"); const roles = Array.isArray(record.required_roles) ? record.required_roles.join(", ") : String(record.required_approver_roles ?? ""); return <Panel key={`${String(record.origin)}-${id}`} title={String(record.request_type ?? "Approval")} subtitle={`${id} · ${String(record.origin ?? "runtime")}`} actions={<Badge tone={status === "Approved" ? "good" : status === "Rejected" ? "danger" : "warn"}>{status}</Badge>}><div className="approval-detail"><div><span>Object</span><strong>{String(record.business_object_type ?? "")} · {String(record.business_object_id ?? "")}</strong></div><div><span>Requested action</span><strong>{String(record.requested_action ?? "")}</strong></div><div><span>Risk tier</span><strong>{String(record.risk_tier ?? "")}</strong></div><div><span>Required roles</span><strong>{roles}</strong></div></div>{record.payload_json !== undefined && <JsonData value={record.payload_json} />}{status === "Pending" && <div className="approval-actions"><button className="primary-button" disabled={busy === id} onClick={() => decide(id, "Approved")}>Approve</button><button className="danger-button" disabled={busy === id} onClick={() => decide(id, "Rejected")}>Reject</button></div>}</Panel>; })}</div>}</div>;
}
