import { useRef, useState } from "react";
import { sendChat } from "../api";
import JsonData from "../components/JsonData";
import Trace from "../components/Trace";
import { Badge, ErrorBox, Panel, Progress } from "../components/UI";
import type { ChatResponse } from "../types";

const examples = [
  "What is the remote-work policy?",
  "Analyze Project Atlas status and identify overloaded team members.",
  "Which region has the highest sales and profit?",
  "Show the current agent hallucination and grounding metrics.",
  "Reassign Task T00025 after checking workload and project risk."
];

const capabilities = [
  ["Policies & documents", "Search authorized enterprise knowledge"],
  ["People & workload", "Review HR and team capacity"],
  ["Projects & sales", "Analyze operational performance"],
  ["Approvals & risk", "Run governed multi-agent workflows"]
];

function AssistantMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className={compact ? "assistant-mark compact" : "assistant-mark"} aria-hidden="true">
      <svg viewBox="0 0 24 24" role="img">
        <path d="M12 3.25a7.25 7.25 0 0 0-6.2 11l-1.05 4.98 4.78-1.48A7.25 7.25 0 1 0 12 3.25Z" />
        <path d="M9 11.75h.01M12 11.75h.01M15 11.75h.01" />
      </svg>
    </span>
  );
}

function PaperclipIcon() {
  return (
    <svg className="button-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="m20.5 11.5-8.42 8.42a6 6 0 0 1-8.49-8.49l9.2-9.19a4 4 0 1 1 5.65 5.65l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg className="button-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export default function AssistantPage() {
  const [message, setMessage] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const messageRef = useRef<HTMLTextAreaElement>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!message.trim() && files.length === 0) {
      setError("Enter a message or attach a file.");
      return;
    }
    setLoading(true); setError(""); setResponse(null);
    try { setResponse(await sendChat(message, files)); }
    catch (err) { setError(err instanceof Error ? err.message : "The workflow failed"); }
    finally { setLoading(false); }
  }

  function useExample(example: string) {
    setMessage(example);
    messageRef.current?.focus();
  }

  return (
    <div className="page-stack assistant-page">
      <header className="assistant-hero">
        <div className="assistant-hero-copy">
          <AssistantMark />
          <div>
            <span className="eyebrow">Secure enterprise intelligence</span>
            <h1>How can I help today?</h1>
            <p>Ask a question, analyze a business workflow, or bring your own documents. Every response is authorized, grounded, and traceable.</p>
          </div>
        </div>
        <div className="assistant-trust-pills" aria-label="Assistant safeguards">
          <span><i className="trust-dot" />Zero-Trust access</span>
          <span>Grounded responses</span>
        </div>
      </header>

      <Panel className="assistant-composer">
        <form onSubmit={submit} className="assistant-form">
          <div className="composer-label">
            <div><AssistantMark compact /><span>Message the enterprise assistant</span></div>
            <span className="composer-security">Authorized sources only</span>
          </div>
          <label className="sr-only" htmlFor="assistant-message">Enterprise request</label>
          <textarea
            id="assistant-message"
            ref={messageRef}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={7}
            placeholder="Ask an enterprise question, request a workflow, or attach a file for analysis…"
          />

          {files.length > 0 && (
            <div className="attached-files" aria-live="polite">
              <span className="attached-files-label">Attached</span>
              <div className="file-pill-list">
                {files.map((file) => (
                  <span className="file-pill" key={`${file.name}-${file.lastModified}`} title={file.name}>
                    <PaperclipIcon />
                    <span>{file.name}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="composer-footer">
            <div className="file-zone">
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.csv,.xlsx"
                onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
              />
              <button type="button" className="secondary-button attach-button" onClick={() => inputRef.current?.click()}>
                <PaperclipIcon />
                Attach files
              </button>
              <span>{files.length ? `${files.length} file${files.length === 1 ? "" : "s"} ready` : "PDF, Word, TXT, CSV, or Excel"}</span>
            </div>
            <button type="submit" className="primary-button run-workflow-button" disabled={loading}>
              <span>{loading ? "Running agents…" : "Run workflow"}</span>
              {!loading && <SendIcon />}
            </button>
          </div>
        </form>

        <div className="prompt-suggestions">
          <div className="suggestion-label"><span>Suggested prompts</span><small>Choose one to get started</small></div>
          <div className="example-row">
            {examples.map((example) => (
              <button type="button" key={example} onClick={() => useExample(example)}>
                <span>{example}</span><span aria-hidden="true">↗</span>
              </button>
            ))}
          </div>
        </div>
      </Panel>

      {error && <ErrorBox message={error} />}

      {!response && !loading && !error && (
        <section className="assistant-empty-state" aria-label="Assistant capabilities">
          <div className="empty-state-heading">
            <AssistantMark compact />
            <div>
              <h2>Start with an enterprise question</h2>
              <p>Ask a policy, HR, project, sales, finance, monitoring, or approval question. You can also attach PDF, Word, TXT, CSV, or Excel files.</p>
            </div>
          </div>
          <div className="capability-grid">
            {capabilities.map(([title, description], index) => (
              <div className="capability-card" key={title}>
                <span>0{index + 1}</span>
                <strong>{title}</strong>
                <p>{description}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {loading && (
        <div className="assistant-running" role="status" aria-live="polite">
          <span className="assistant-running-orbit"><i /></span>
          <div><strong>Coordinating secure agents</strong><span>Authorizing the request, retrieving evidence, and validating the response…</span></div>
        </div>
      )}

      {response && (
        <div className="assistant-response-area">
          <div className="result-header assistant-result-header">
            <div>
              <Badge tone={response.status === "Completed" ? "good" : response.status === "Access Denied" ? "danger" : "warn"}>{response.status}</Badge>
              <span><strong>{response.workflow_id}</strong> · {response.workflow_name}</span>
            </div>
            <span>Run {response.workflow_run_id}</span>
          </div>

          <div className="two-column result-grid assistant-primary-results">
            <Panel className="result-panel response-panel" title="Final enterprise response" subtitle="Grounded and validated output">
              <div className="answer-label"><AssistantMark compact /><span>Assistant response</span></div>
              <ul className="answer-text answer-points">{response.answer.split("\n").map((line) => line.trim()).filter(Boolean).map((line, index) => <li key={index}>{line.replace(/^(?:[-*+\u2022]|\d+[.)])\s+/, "")}</li>)}</ul>
              <div className="score-grid"><Progress value={response.confidence * 100} label="Confidence" /><Progress value={response.grounding_score * 100} label="Grounding" /></div>
              {response.warnings.length > 0 && <div className="warning-list">{response.warnings.map((warning) => <div key={warning}>{warning}</div>)}</div>}
              {response.approval.required && <div className="approval-banner"><strong>Human approval required</strong><span>{response.approval.approval_id} · Roles: {response.approval.required_roles.join(", ")}</span></div>}
            </Panel>
            <Panel className="result-panel security-panel" title="Zero-Trust decision" subtitle="Deterministic authorization, not an LLM guess">
              <div className="decision-card"><Badge tone={response.security.decision === "ALLOW" ? "good" : "danger"}>{response.security.decision}</Badge><h3>{response.security.permission}</h3><p>{response.security.reason}</p><small>Session risk score: {response.security.session_risk_score.toFixed(3)}</small></div>
              <div className="tag-list">{response.security.zero_trust_checks.map((check) => <span key={check}>{check.replace(/_/g, " ")}</span>)}</div>
            </Panel>
          </div>

          <div className="two-column assistant-secondary-results">
            <Panel className="result-panel trace-panel" title="Agent execution trace" subtitle="Visible multi-agent workflow"><Trace agents={response.agents} /></Panel>
            <Panel className="result-panel evidence-panel" title="Evidence sources" subtitle={`${response.sources.length} authorized sources`}>
              <div className="source-list">{response.sources.map((source, index) => <div key={`${source.source_id}-${index}`}><strong>{source.title}</strong><span>{source.source_type}{source.section ? ` · ${source.section}` : ""}</span>{source.score !== undefined && <small>Similarity {source.score.toFixed(3)}</small>}</div>)}</div>
            </Panel>
          </div>

          <div className="assistant-detail-results">
            {response.sections.map((section, index) => <Panel className="result-panel detail-panel" key={index} title={String(section.title ?? `Agent result ${index + 1}`)} subtitle={String(section.summary ?? "")}><JsonData value={section.content} /></Panel>)}
            <Panel className="result-panel explainability-panel" title="Explainability record" subtitle="Why the system selected this route and confidence"><JsonData value={response.explanation} /></Panel>
          </div>
        </div>
      )}
    </div>
  );
}
