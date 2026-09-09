import { useEffect, useState } from "react";
import { backendConfigured, me } from "./api";
import Sidebar from "./components/Sidebar";
import { Loading } from "./components/UI";
import ApprovalsPage from "./pages/ApprovalsPage";
import AssistantPage from "./pages/AssistantPage";
import AuditPage from "./pages/AuditPage";
import DocumentsPage from "./pages/DocumentsPage";
import HRPage from "./pages/HRPage";
import LoginPage from "./pages/LoginPage";
import ModelsPage from "./pages/ModelsPage";
import MonitoringPage from "./pages/MonitoringPage";
import OverviewPage from "./pages/OverviewPage";
import ProjectsPage from "./pages/ProjectsPage";
import SalesPage from "./pages/SalesPage";
import type { PageKey, UserProfile } from "./types";

export default function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [page, setPage] = useState<PageKey>("overview");
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!backendConfigured) { setChecking(false); return; }
    if (!localStorage.getItem("enterprise_token")) { setChecking(false); return; }
    me().then(setUser).catch(() => localStorage.removeItem("enterprise_token")).finally(() => setChecking(false));
  }, []);

  if (!backendConfigured) return <main className="center-screen"><section className="login-card"><h1>Assistant service is not connected yet</h1><p>The dashboard has been published. Sign-in, document analysis, and AI responses will be available once the assistant service is connected.</p></section></main>;
  if (checking) return <div className="center-screen"><Loading label="Restoring secure session" /></div>;
  if (!user) return <LoginPage onLogin={(token, profile) => { localStorage.setItem("enterprise_token", token); setUser(profile); }} />;

  const content = {
    overview: <OverviewPage />,
    assistant: <AssistantPage />,
    projects: <ProjectsPage />,
    hr: <HRPage />,
    sales: <SalesPage />,
    documents: <DocumentsPage />,
    approvals: <ApprovalsPage />,
    monitoring: <MonitoringPage />,
    models: <ModelsPage />,
    audit: <AuditPage />
  }[page];

  return (
    <div className="app-shell">
      <Sidebar page={page} onPage={setPage} user={user} onLogout={() => { localStorage.removeItem("enterprise_token"); setUser(null); setPage("overview"); }} />
      <main className="content-shell">
        <header className="topbar"><div><strong>Secure Multi-Agent Enterprise Assistant</strong><span>RAG · RBAC · HITL · XAI · Monitoring</span></div><div className="session-pill"><span className="status-dot" />Authenticated as {user.roles.join(" / ")}</div></header>
        <div className="content-area">{content}</div>
      </main>
    </div>
  );
}
