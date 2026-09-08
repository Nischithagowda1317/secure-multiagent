import { useEffect, useRef, useState } from "react";
import { get, uploadDocument } from "../api";
import { DataTable, ErrorBox, Loading, Panel } from "../components/UI";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [classification, setClassification] = useState("Internal");
  const [roles, setRoles] = useState("Admin|Executive|HR_Manager|Project_Manager|Finance_Manager|Sales_Manager|Security_Officer|Employee|Auditor|AI_Reviewer");
  const [permission, setPermission] = useState("document.read_public");
  function refresh() { setLoading(true); get<Array<Record<string, unknown>>>("/documents").then(setDocuments).catch((err: Error) => setError(err.message)).finally(() => setLoading(false)); }
  useEffect(refresh, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError(""); setNotice("");
    const file = fileRef.current?.files?.[0]; if (!file) { setError("Choose a document first."); return; }
    const form = new FormData(); form.append("file", file); form.append("title", title || file.name); form.append("classification", classification); form.append("allowed_roles", roles); form.append("required_permission", permission);
    try { const result = await uploadDocument(form); setNotice(`Uploaded and indexed ${String(result.title ?? file.name)}.`); setTitle(""); if (fileRef.current) fileRef.current.value = ""; refresh(); } catch (err) { setError(err instanceof Error ? err.message : "Upload failed"); }
  }
  return <div className="page-stack"><div className="page-title"><div><span className="eyebrow">Secure RAG knowledge base</span><h1>Enterprise documents</h1><p>Canonical PDF/DOCX policies plus authorized uploads. Role and permission filters are applied before retrieval.</p></div></div>{error && <ErrorBox message={error} />}{notice && <div className="success-box">{notice}</div>}<Panel title="Publish an enterprise document" subtitle="Requires document.upload. Temporary chat attachments do not require publication."><form className="document-form" onSubmit={submit}><label>File<input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.csv,.xlsx" required /></label><label>Display title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Optional" /></label><label>Classification<select value={classification} onChange={(event) => setClassification(event.target.value)}><option>Internal</option><option>Confidential</option><option>Restricted</option></select></label><label>Required permission<input value={permission} onChange={(event) => setPermission(event.target.value)} /></label><label className="wide">Allowed roles<input value={roles} onChange={(event) => setRoles(event.target.value)} /></label><button className="primary-button">Upload and index</button></form></Panel><Panel title="Authorized document catalogue" subtitle={`${documents.length} documents visible to your role`}>{loading ? <Loading /> : <DataTable rows={documents} maxRows={40} />}</Panel></div>;
}
