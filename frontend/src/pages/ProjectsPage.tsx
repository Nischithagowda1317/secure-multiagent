import { useEffect, useState } from "react";
import { get } from "../api";
import JsonData from "../components/JsonData";
import { Badge, DataTable, ErrorBox, Loading, Panel, Progress } from "../components/UI";

interface Project {
  project_id: string;
  project_name: string;
  description: string;
  current_status: string;
  priority: string;
  current_progress_percent: number;
  expected_progress_percent: number;
  risk_level: string;
  planned_end_date: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { get<Project[]>("/dashboard/projects").then((items) => { setProjects(items); setSelected(items[0] ?? null); }).catch((err: Error) => setError(err.message)); }, []);
  useEffect(() => { if (selected) get<Record<string, unknown>>(`/dashboard/projects/${selected.project_id}`).then(setDetail).catch((err: Error) => setError(err.message)); }, [selected]);
  if (error) return <ErrorBox message={error} />;
  if (!projects.length) return <Loading label="Loading project portfolio" />;
  const detailValue = detail as { tasks?: Array<Record<string, unknown>>; members?: Array<Record<string, unknown>>; risks?: Array<Record<string, unknown>> } | null;
  return (
    <div className="page-stack">
      <div className="page-title"><div><span className="eyebrow">Project Agent data domain</span><h1>Project portfolio</h1><p>Progress, deadlines, task status, resource allocation, and risk registers.</p></div></div>
      <div className="project-layout">
        <Panel title="Projects" subtitle={`${projects.length} active records`}>
          <div className="project-list">{projects.map((project) => <button key={project.project_id} className={selected?.project_id === project.project_id ? "selected" : ""} onClick={() => { setSelected(project); setDetail(null); }}><div><strong>{project.project_name}</strong><span>{project.project_id} · {project.priority}</span></div><Badge tone={project.current_status === "At Risk" ? "warn" : "good"}>{project.current_status}</Badge></button>)}</div>
        </Panel>
        <div className="page-stack">
          {selected && <Panel title={selected.project_name} subtitle={selected.description} actions={<Badge tone={selected.risk_level === "High" ? "danger" : selected.risk_level === "Medium" ? "warn" : "good"}>{selected.risk_level} risk</Badge>}>
            <div className="project-metrics"><Progress value={selected.current_progress_percent} label="Current progress" /><Progress value={selected.expected_progress_percent} label="Expected progress" /></div>
            <div className="mini-stat-row"><div><span>Status</span><strong>{selected.current_status}</strong></div><div><span>Priority</span><strong>{selected.priority}</strong></div><div><span>Planned end</span><strong>{selected.planned_end_date}</strong></div></div>
          </Panel>}
          {!detailValue ? <Loading label="Loading project details" /> : <>
            <Panel title="Tasks" subtitle={`${detailValue.tasks?.length ?? 0} project tasks`}><DataTable rows={detailValue.tasks ?? []} maxRows={20} /></Panel>
            <div className="two-column"><Panel title="Team allocation"><DataTable rows={detailValue.members ?? []} maxRows={12} /></Panel><Panel title="Risk register"><DataTable rows={detailValue.risks ?? []} maxRows={12} /></Panel></div>
          </>}
        </div>
      </div>
    </div>
  );
}
