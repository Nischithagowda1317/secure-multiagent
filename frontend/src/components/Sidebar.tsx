import type { PageKey, UserProfile } from "../types";

const navigation: Array<{ key: PageKey; label: string; code: string }> = [
  { key: "overview", label: "Overview", code: "OV" },
  { key: "assistant", label: "AI Assistant", code: "AI" },
  { key: "projects", label: "Projects", code: "PR" },
  { key: "hr", label: "Workforce", code: "HR" },
  { key: "sales", label: "Sales", code: "SA" },
  { key: "documents", label: "Knowledge Base", code: "KB" },
  { key: "approvals", label: "Approvals", code: "AP" },
  { key: "monitoring", label: "Monitoring", code: "MO" },
  { key: "models", label: "Model Center", code: "ML" },
  { key: "audit", label: "Audit Logs", code: "AU" }
];

export default function Sidebar({ page, onPage, user, onLogout }: {
  page: PageKey;
  onPage: (page: PageKey) => void;
  user: UserProfile;
  onLogout: () => void;
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">NC</div>
        <div><strong>NexaCore</strong><span>Enterprise Intelligence</span></div>
      </div>
      <nav>
        {navigation.map((item) => (
          <button key={item.key} className={page === item.key ? "active" : ""} onClick={() => onPage(item.key)}>
            <span className="nav-code">{item.code}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-user">
        <div className="avatar">{user.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</div>
        <div className="sidebar-user-copy"><strong>{user.full_name}</strong><span>{user.roles.join(" · ")}</span></div>
        <button className="logout" onClick={onLogout}>Sign out</button>
      </div>
    </aside>
  );
}
