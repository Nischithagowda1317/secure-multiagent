import { useEffect, useState } from "react";
import { get } from "../api";
import { BarList, DataTable, ErrorBox, Loading, Panel } from "../components/UI";

interface HRData {
  headcount_by_department: Record<string, number>;
  workload_status: Record<string, number>;
  top_overtime: Array<Record<string, unknown>>;
}

export default function HRPage() {
  const [data, setData] = useState<HRData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { get<HRData>("/dashboard/hr").then(setData).catch((err: Error) => setError(err.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading label="Loading workforce analytics" />;
  const departments = Object.entries(data.headcount_by_department).map(([department, count]) => ({ department, count }));
  const workload = Object.entries(data.workload_status).map(([status, count]) => ({ status, count }));
  return (
    <div className="page-stack">
      <div className="page-title"><div><span className="eyebrow">HR Agent and workload model</span><h1>Workforce intelligence</h1><p>Authorized headcount, capacity, overtime, and workload status analysis.</p></div></div>
      <div className="two-column"><Panel title="Headcount by department"><BarList items={departments.slice(0, 12)} valueKey="count" labelKey="department" /></Panel><Panel title="Predicted workload status"><BarList items={workload} valueKey="count" labelKey="status" /></Panel></div>
      <Panel title="Highest year-to-date overtime" subtitle="Use the assistant for deeper department or employee analysis"><DataTable rows={data.top_overtime} /></Panel>
    </div>
  );
}
