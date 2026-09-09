(() => {
  "use strict";
  const root = document.getElementById("root");
  const API = (window.ENTERPRISE_CONFIG?.apiBaseUrl ?? "/api").replace(/\/+$/, "");
  const state = {
    token: localStorage.getItem("enterprise_token"),
    user: null,
    page: "overview",
    accounts: [],
    chat: null,
    files: [],
  };

  const NAV = [
    ["overview", "Overview", "OV"], ["assistant", "AI Assistant", "AI"],
    ["projects", "Projects", "PR"], ["hr", "Workforce", "HR"],
    ["sales", "Sales", "SA"], ["documents", "Knowledge Base", "KB"],
    ["approvals", "Approvals", "AP"], ["monitoring", "Monitoring", "MO"],
    ["models", "Model Center", "ML"], ["audit", "Audit Logs", "AU"]
  ];
  const EXAMPLES = [
    "What is the remote-work policy?",
    "Analyze Project Atlas status and identify overloaded team members.",
    "Which region has the highest sales and profit?",
    "Show the current agent hallucination and grounding metrics.",
    "Reassign Task T00025 after checking workload and project risk.",
    "Show the annual salary of employee E0013."
  ];

  const esc = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
  const humanize = (value) => String(value).replace(/_/g, " ").replace(/\b\w/g, (x) => x.toUpperCase());
  const money = (value) => new Intl.NumberFormat("en-US", {style:"currency", currency:"USD", maximumFractionDigits:0}).format(Number(value || 0));
  const number = (value) => new Intl.NumberFormat("en-US", {maximumFractionDigits:2}).format(Number(value || 0));
  const tone = (value) => /allow|approved|completed|pass|success|active|low/i.test(String(value)) ? "good" : /deny|reject|failed|error|high risk/i.test(String(value)) ? "danger" : /pending|await|review|risk|medium/i.test(String(value)) ? "warn" : "neutral";
  const badge = (value, selectedTone) => `<span class="badge ${selectedTone || tone(value)}">${esc(value)}</span>`;
  const loading = (label="Loading") => `<div class="loading"><span class="spinner"></span>${esc(label)}</div>`;
  const errorBox = (message) => `<div class="error-box">${esc(message)}</div>`;
  const panel = (title, body, subtitle="", actions="", className="") => `<section class="panel ${esc(className)}"><header class="panel-header"><div><h2>${esc(title)}</h2>${subtitle ? `<p>${esc(subtitle)}</p>` : ""}</div>${actions ? `<div class="panel-actions">${actions}</div>` : ""}</header><div class="panel-body">${body}</div></section>`;
  const assistantMark = (compact=false) => `<span class="assistant-mark${compact ? " compact" : ""}" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3.25a7.25 7.25 0 0 0-6.2 11l-1.05 4.98 4.78-1.48A7.25 7.25 0 1 0 12 3.25Z"></path><path d="M9 11.75h.01M12 11.75h.01M15 11.75h.01"></path></svg></span>`;
  const paperclipIcon = () => `<svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m20.5 11.5-8.42 8.42a6 6 0 0 1-8.49-8.49l9.2-9.19a4 4 0 1 1 5.65 5.65l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>`;
  const sendIcon = () => `<svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"></path></svg>`;
  const stat = (label, value, helper="", statTone="default") => `<div class="stat-card ${statTone}"><span class="stat-label">${esc(label)}</span><strong class="stat-value">${esc(value)}</strong>${helper ? `<span class="stat-helper">${esc(helper)}</span>` : ""}</div>`;
  const progress = (value, label) => { const v=Math.max(0,Math.min(100,Number(value)||0)); return `<div class="progress-wrap"><div class="progress-label"><span>${esc(label)}</span><strong>${v.toFixed(0)}%</strong></div><div class="progress-track"><span style="width:${v}%"></span></div></div>`; };
  const formatCell = (value) => {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (typeof value === "number") return number(value);
    if (typeof value === "object") return `<details><summary>View</summary><pre class="code-block">${esc(JSON.stringify(value,null,2))}</pre></details>`;
    const text=String(value); return text.length>130 ? `<details><summary>${esc(text.slice(0,80))}…</summary><div>${esc(text)}</div></details>` : esc(text);
  };
  const table = (rows, maxRows=30) => {
    if (!Array.isArray(rows) || !rows.length) return `<div class="empty-state">No records found.</div>`;
    const cols=Object.keys(rows[0]).slice(0,10);
    return `<div class="table-scroll"><table><thead><tr>${cols.map(c=>`<th>${esc(humanize(c))}</th>`).join("")}</tr></thead><tbody>${rows.slice(0,maxRows).map(row=>`<tr>${cols.map(c=>`<td>${formatCell(row[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  };
  const jsonView = (value) => {
    if (value === null || value === undefined) return "—";
    if (Array.isArray(value)) return value.length && typeof value[0] === "object" ? table(value) : `<div class="tag-list">${value.map(x=>`<span>${esc(x)}</span>`).join("")}</div>`;
    if (typeof value !== "object") return esc(value);
    return `<div class="key-grid">${Object.entries(value).map(([k,v])=>`<div class="key-row"><span>${esc(humanize(k))}</span><div>${jsonView(v)}</div></div>`).join("")}</div>`;
  };
  const barList = (items, labelKey, valueKey) => {
    if (!items?.length) return `<div class="empty-state">No data.</div>`;
    const max=Math.max(...items.map(x=>Number(x[valueKey]||0)),1);
    return `<div class="bar-list">${items.map(item=>{const v=Number(item[valueKey]||0); return `<div class="bar-item"><div class="bar-row"><span>${esc(item[labelKey])}</span><strong>${number(v)}</strong></div><div class="bar-track"><span style="width:${v/max*100}%"></span></div></div>`}).join("")}</div>`;
  };

  async function request(path, options={}) {
    const headers = new Headers(options.headers || {});
    if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
    const response = await fetch(`${API}${path}`, {...options, headers});
    let body;
    try { body = await response.json(); } catch { body = null; }
    if (!response.ok) {
      if (response.status === 401 && path !== "/auth/login") logout(false);
      throw new Error(body?.detail || `${response.status} ${response.statusText}`);
    }
    return body;
  }
  const get = (path) => request(path);
  const post = (path, body) => request(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});

  function renderLogin(error="") {
    root.innerHTML = `<main class="login-shell"><section class="login-hero"><div class="hero-badge">Secure enterprise intelligence</div><h1>Autonomous workflows.<br>Deterministic security.</h1><p>A complete implementation of multi-agent coordination, secure RAG, role-based access, human approval, explainability, and reliability monitoring.</p><div class="hero-grid"><div><strong>11</strong><span>Specialized agents</span></div><div><strong>12</strong><span>Workflow definitions</span></div><div><strong>50</strong><span>Linked data tables</span></div><div><strong>14</strong><span>Knowledge documents</span></div></div></section><section class="login-panel"><div class="login-card"><div class="brand login-brand"><div class="brand-mark">NC</div><div><strong>NexaCore</strong><span>Enterprise AI Assistant</span></div></div><h2>Sign in to the demonstration</h2><p>Choose a synthetic account. Use the Employee role to demonstrate access denial and elevated roles for authorized workflows.</p><div id="login-error">${error ? errorBox(error) : ""}</div><form id="login-form"><label>Email address<input id="login-email" type="email" required></label><label>Password<input id="login-password" type="password" value="Demo@123!" required></label><button class="primary-button" id="login-button">Sign in</button></form><div class="account-picker"><span>Quick role selection</span><div id="account-list" class="account-list">${loading("Loading accounts")}</div></div></div></section></main>`;
    document.getElementById("login-form").addEventListener("submit", login);
    loadAccounts();
  }

  async function loadAccounts() {
    try {
      state.accounts = await request("/auth/demo-accounts");
      const list=document.getElementById("account-list");
      if (!list) return;
      if (!state.accounts.length) {
        list.innerHTML='<p role="status">No sign-in accounts are available yet. Ask your administrator to finish setting up this workspace.</p>';
        return;
      }
      list.innerHTML=state.accounts.map((account,index)=>`<button type="button" data-account="${index}"><strong>${esc(account.roles.filter(r=>r!=="Employee").join(" / ")||"Employee")}</strong><small>${esc(account.email)}</small></button>`).join("");
      list.querySelectorAll("button").forEach(button=>button.addEventListener("click",()=>selectAccount(Number(button.dataset.account))));
      const preferred=state.accounts.findIndex(a=>a.roles.includes("Admin"));
      selectAccount(preferred>=0?preferred:0);
    } catch (error) { const list=document.getElementById("account-list"); if(list) list.innerHTML=errorBox(error.message); }
  }
  function selectAccount(index) {
    const account=state.accounts[index]; if(!account)return;
    document.getElementById("login-email").value=account.email;
    document.getElementById("login-password").value=account.temporary_password;
    document.querySelectorAll("#account-list button").forEach((button,i)=>button.classList.toggle("selected",i===index));
  }
  async function login(event) {
    event.preventDefault();
    const button=document.getElementById("login-button"); button.disabled=true; button.textContent="Signing in…";
    try {
      const data=await request("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:document.getElementById("login-email").value,password:document.getElementById("login-password").value})});
      state.token=data.access_token; state.user=data.user; localStorage.setItem("enterprise_token",state.token); state.page="overview"; renderShell();
    } catch(error) { document.getElementById("login-error").innerHTML=errorBox(error.message); }
    finally { button.disabled=false; button.textContent="Sign in"; }
  }
  function logout(render=true) { state.token=null; state.user=null; localStorage.removeItem("enterprise_token"); if(render)renderLogin(); }

  function renderShell() {
    const initials=state.user.full_name.split(" ").map(x=>x[0]).slice(0,2).join("");
    root.innerHTML=`<div class="app-shell"><aside class="sidebar"><div class="brand"><div class="brand-mark">NC</div><div><strong>NexaCore</strong><span>Enterprise Intelligence</span></div></div><nav class="plain-nav" id="nav">${NAV.map(([key,label,code])=>`<button data-page="${key}" class="${state.page===key?"active":""}"><span class="nav-code">${code}</span><span>${label}</span></button>`).join("")}</nav><div class="sidebar-user"><div class="avatar">${esc(initials)}</div><div class="sidebar-user-copy"><strong>${esc(state.user.full_name)}</strong><span>${esc(state.user.roles.join(" · "))}</span></div><button id="logout" class="logout">Sign out</button></div></aside><main class="content-shell"><header class="topbar"><div><strong>Secure Multi-Agent Enterprise Assistant</strong><span>RAG · RBAC · HITL · XAI · Monitoring</span></div><div class="session-pill"><span class="status-dot"></span>Authenticated as ${esc(state.user.roles.join(" / "))}</div></header><div class="content-area" id="content">${loading("Loading page")}</div></main></div>`;
    document.getElementById("logout").addEventListener("click",()=>logout());
    document.querySelectorAll("#nav button").forEach(button=>button.addEventListener("click",()=>{state.page=button.dataset.page; renderShell();}));
    renderPage();
  }
  const pageTitle=(eye,title,copy)=>`<div class="page-title"><div><span class="eyebrow">${esc(eye)}</span><h1>${esc(title)}</h1><p>${esc(copy)}</p></div></div>`;
  async function renderPage() {
    const content=document.getElementById("content");
    try {
      if(state.page==="overview") await overviewPage(content);
      else if(state.page==="assistant") assistantPage(content);
      else if(state.page==="projects") await projectsPage(content);
      else if(state.page==="hr") await hrPage(content);
      else if(state.page==="sales") await salesPage(content);
      else if(state.page==="documents") await documentsPage(content);
      else if(state.page==="approvals") await approvalsPage(content);
      else if(state.page==="monitoring") await monitoringPage(content);
      else if(state.page==="models") await modelsPage(content);
      else if(state.page==="audit") await auditPage(content);
    } catch(error) { content.innerHTML=`<div class="page-stack">${pageTitle("Access or data error",humanize(state.page),"The requested dashboard module could not be loaded.")}${errorBox(error.message)}</div>`; }
  }

  async function overviewPage(content) {
    const d=await get("/dashboard/overview");
    const workflowRows=Object.entries(d.workflows).map(([status,count])=>({status,count}));
    content.innerHTML=`<div class="page-stack">${pageTitle(`Dataset snapshot ${d.snapshot_date}`,"Enterprise overview",`Operational, security, AI-quality, and workflow indicators for ${d.company}.`)}<div class="stat-grid five">${stat("Projects",d.projects.total,`${d.projects.at_risk} at risk`,d.projects.at_risk?"warn":"good")}${stat("Sales Orders",Number(d.sales.orders).toLocaleString(),money(d.sales.sales_usd))}${stat("Total Profit",money(d.sales.profit_usd),"Curated sales dataset","good")}${stat("Pending Approvals",d.approvals.pending_source+d.approvals.pending_runtime,"Dataset and live requests","warn")}${stat("Knowledge Chunks",d.dataset_counts.rag_chunks,`${d.dataset_counts.document_catalog} documents`)}</div><div class="two-column">${panel("Workflow outcomes",barList(workflowRows,"status","count"),"Historical multi-agent run status distribution")}${panel("Implementation coverage",`<div class="coverage-grid">${Object.entries(d.dataset_counts).map(([k,v])=>`<div><span>${esc(humanize(k))}</span><strong>${Number(v).toLocaleString()}</strong></div>`).join("")}</div>`,"Data volume available to specialist agents")}</div><div class="two-column">${panel("Project health",`<div class="mini-stat-row"><div><span>Total projects</span><strong>${d.projects.total}</strong></div><div><span>At risk</span><strong>${d.projects.at_risk}</strong></div><div><span>High risk</span><strong>${d.projects.high_risk}</strong></div></div>`)}${panel("Workforce capacity",d.workforce?`<div class="mini-stat-row"><div><span>Employees</span><strong>${d.workforce.employees}</strong></div><div><span>High workload</span><strong>${d.workforce.high_or_overloaded}</strong></div><div><span>Overloaded</span><strong>${d.workforce.overloaded}</strong></div></div>`:`<p class="muted">Restricted by your role. Sign in as HR Manager, Executive, Auditor, AI Reviewer, or Admin.</p>`)}</div></div>`;
  }

  function assistantPage(content) {
    const filePills=()=>state.files.length?`<div class="attached-files"><span class="attached-files-label">Attached</span><div class="file-pill-list">${state.files.map(file=>`<span class="file-pill" title="${esc(file.name)}">${paperclipIcon()}<span>${esc(file.name)}</span></span>`).join("")}</div></div>`:"";
    const empty=`<section class="assistant-empty-state" aria-label="Assistant capabilities"><div class="empty-state-heading">${assistantMark(true)}<div><h2>Start with an enterprise question</h2><p>Ask a policy, HR, project, sales, finance, monitoring, or approval question. You can also attach PDF, Word, TXT, CSV, or Excel files.</p></div></div><div class="capability-grid">${[["Policies & documents","Search authorized enterprise knowledge"],["People & workload","Review HR and team capacity"],["Projects & sales","Analyze operational performance"],["Approvals & risk","Run governed multi-agent workflows"]].map(([title,description],index)=>`<div class="capability-card"><span>0${index+1}</span><strong>${title}</strong><p>${description}</p></div>`).join("")}</div></section>`;
    content.innerHTML=`<div class="page-stack assistant-page"><header class="assistant-hero"><div class="assistant-hero-copy">${assistantMark()}<div><span class="eyebrow">Secure enterprise intelligence</span><h1>How can I help today?</h1><p>Ask a question, analyze a business workflow, or bring your own documents. Every response is authorized, grounded, and traceable.</p></div></div><div class="assistant-trust-pills" aria-label="Assistant safeguards"><span><i class="trust-dot"></i>Zero-Trust access</span><span>Grounded responses</span></div></header><section class="panel assistant-composer"><div class="panel-body"><form id="chat-form" class="assistant-form"><div class="composer-label"><div>${assistantMark(true)}<span>Message the enterprise assistant</span></div><span class="composer-security">Authorized sources only</span></div><label class="sr-only" for="chat-message">Enterprise request</label><textarea id="chat-message" rows="7" placeholder="Ask an enterprise question, request a workflow, or attach a file for analysis…"></textarea><div id="attached-files">${filePills()}</div><div class="composer-footer"><div class="file-zone"><input id="chat-files" type="file" multiple accept=".pdf,.docx,.txt,.csv,.xlsx"><button type="button" id="attach" class="secondary-button attach-button">${paperclipIcon()}Attach files</button><span id="file-helper">${state.files.length?`${state.files.length} file${state.files.length===1?"":"s"} ready`:"PDF, Word, TXT, CSV, or Excel"}</span></div><button id="chat-button" class="primary-button run-workflow-button"><span>Run workflow</span>${sendIcon()}</button></div></form><div class="prompt-suggestions"><div class="suggestion-label"><span>Suggested prompts</span><small>Choose one to get started</small></div><div class="example-row">${EXAMPLES.map((x,i)=>`<button type="button" data-example="${i}"><span>${esc(x)}</span><span aria-hidden="true">↗</span></button>`).join("")}</div></div></div></section><div id="chat-error"></div><div id="chat-result">${empty}</div></div>`;
    const files=document.getElementById("chat-files");
    document.getElementById("attach").addEventListener("click",()=>files.click());
    files.addEventListener("change",()=>{state.files=Array.from(files.files||[]);document.getElementById("attached-files").innerHTML=filePills();document.getElementById("file-helper").textContent=state.files.length?`${state.files.length} file${state.files.length===1?"":"s"} ready`:"PDF, Word, TXT, CSV, or Excel";});
    document.querySelectorAll("[data-example]").forEach(button=>button.addEventListener("click",()=>{const message=document.getElementById("chat-message");message.value=EXAMPLES[Number(button.dataset.example)];message.focus();}));
    document.getElementById("chat-form").addEventListener("submit",runChat);
  }
  async function runChat(event) {
    event.preventDefault();
    const button=document.getElementById("chat-button"), result=document.getElementById("chat-result"), error=document.getElementById("chat-error");
    const message=document.getElementById("chat-message").value;
    if(!message.trim() && state.files.length===0){error.innerHTML=errorBox("Enter a message or attach a file.");return;}
    error.innerHTML=""; result.innerHTML=`<div class="assistant-running" role="status"><span class="assistant-running-orbit"><i></i></span><div><strong>Coordinating secure agents</strong><span>Authorizing the request, retrieving evidence, and validating the response…</span></div></div>`; button.disabled=true; button.innerHTML="<span>Running agents…</span>";
    const form=new FormData(); form.append("message",message); state.files.forEach(file=>form.append("files",file));
    try { state.chat=await request("/chat",{method:"POST",body:form}); result.innerHTML=renderChatResult(state.chat); }
    catch(err){result.innerHTML="";error.innerHTML=errorBox(err.message);} finally{button.disabled=false;button.innerHTML=`<span>Run workflow</span>${sendIcon()}`;}
  }
  function renderChatResult(r) {
    const sources=`<div class="source-list">${r.sources.map(s=>`<div><strong>${esc(s.title)}</strong><span>${esc(s.source_type)}${s.section?` · ${esc(s.section)}`:""}</span>${s.score!==null&&s.score!==undefined?`<small>Similarity ${Number(s.score).toFixed(3)}</small>`:""}${s.path?`<small class="source-path">${esc(s.path)}</small>`:""}</div>`).join("")||"<div class='empty-state'>No sources returned.</div>"}</div>`;
    const trace=`<div class="trace">${r.agents.map(a=>`<div class="trace-row"><div class="trace-node">${esc(a.agent_id)}</div><div class="trace-line"></div><div class="trace-card"><div><strong>${esc(a.agent_name)}</strong>${badge(a.status,"good")}</div><p>${esc(a.summary)}</p><small>${a.duration_ms} ms · Confidence ${(a.confidence*100).toFixed(0)}%</small></div></div>`).join("")}</div>`;
    const warnings=r.warnings?.length?`<div class="warning-list">${r.warnings.map(w=>`<div>${esc(w)}</div>`).join("")}</div>`:"";
    const approval=r.approval?.required?`<div class="approval-banner"><strong>Human approval required</strong><span>${esc(r.approval.approval_id)} · Roles: ${esc(r.approval.required_roles.join(", "))}</span></div>`:"";
    return `<div class="assistant-response-area"><div class="result-header assistant-result-header"><div>${badge(r.status)}<span><strong>${esc(r.workflow_id)}</strong> · ${esc(r.workflow_name)}</span></div><span>Run ${esc(r.workflow_run_id)}</span></div><div class="two-column result-grid assistant-primary-results">${panel("Final enterprise response",`<div class="answer-label">${assistantMark(true)}<span>Assistant response</span></div><ul class="answer-text answer-points">${r.answer.split("\n").map(line=>line.trim()).filter(Boolean).map(line=>`<li>${esc(line.replace(/^(?:[-*+\u2022]|\d+[.)])\s+/, ""))}</li>`).join("")}</ul><div class="score-grid">${progress(r.confidence*100,"Confidence")}${progress(r.grounding_score*100,"Grounding")}</div>${warnings}${approval}`,"Grounded and validated output","","result-panel response-panel")}${panel("Zero-Trust decision",`<div class="decision-card">${badge(r.security.decision)}<h3>${esc(r.security.permission)}</h3><p>${esc(r.security.reason)}</p><small>Session risk score: ${Number(r.security.session_risk_score).toFixed(3)}</small></div><div class="tag-list">${r.security.zero_trust_checks.map(x=>`<span>${esc(humanize(x))}</span>`).join("")}</div>`,"Deterministic authorization, not an LLM guess","","result-panel security-panel")}</div><div class="two-column assistant-secondary-results">${panel("Agent execution trace",trace,"Visible multi-agent workflow","","result-panel trace-panel")}${panel("Evidence sources",sources,`${r.sources.length} authorized sources`,"","result-panel evidence-panel")}</div><div class="assistant-detail-results">${(r.sections||[]).map((s,i)=>panel(s.title||`Agent result ${i+1}`,jsonView(s.content),s.summary||"","","result-panel detail-panel")).join("")}${panel("Explainability record",jsonView(r.explanation),"Why the system selected this route and confidence","","result-panel explainability-panel")}</div></div>`;
  }

  async function projectsPage(content) {
    const projects=await get("/dashboard/projects");
    content.innerHTML=`<div class="page-stack">${pageTitle("Project Agent data domain","Project portfolio","Progress, deadlines, task status, resource allocation, and risk registers.")}<div class="project-layout">${panel("Projects",`<div class="project-list" id="project-list">${projects.map((p,i)=>`<button data-project="${i}" class="${i===0?"selected":""}"><div><strong>${esc(p.project_name)}</strong><span>${esc(p.project_id)} · ${esc(p.priority)}</span></div>${badge(p.current_status)}</button>`).join("")}</div>`,`${projects.length} project records`)}<div id="project-detail">${loading("Loading project details")}</div></div></div>`;
    document.querySelectorAll("[data-project]").forEach(button=>button.addEventListener("click",()=>{document.querySelectorAll("[data-project]").forEach(b=>b.classList.remove("selected"));button.classList.add("selected");loadProject(projects[Number(button.dataset.project)]);}));
    if(projects[0])loadProject(projects[0]);
  }
  async function loadProject(p) {
    const target=document.getElementById("project-detail"); target.innerHTML=loading("Loading project details");
    try { const d=await get(`/dashboard/projects/${p.project_id}`); target.innerHTML=`<div class="page-stack">${panel(p.project_name,`<div class="project-metrics">${progress(p.current_progress_percent,"Current progress")}${progress(p.expected_progress_percent,"Expected progress")}</div><div class="mini-stat-row"><div><span>Status</span><strong>${esc(p.current_status)}</strong></div><div><span>Priority</span><strong>${esc(p.priority)}</strong></div><div><span>Planned end</span><strong>${esc(p.planned_end_date)}</strong></div></div>`,p.description,badge(`${p.risk_level} risk`))}${panel("Tasks",table(d.tasks,20),`${d.tasks.length} project tasks`)}<div class="two-column">${panel("Team allocation",table(d.members,12))}${panel("Risk register",table(d.risks,12))}</div></div>`;} catch(e){target.innerHTML=errorBox(e.message);}
  }

  async function hrPage(content) {
    const d=await get("/dashboard/hr");
    const head=Object.entries(d.headcount_by_department).map(([department,count])=>({department,count}));
    const workload=Object.entries(d.workload_status).map(([status,count])=>({status,count}));
    content.innerHTML=`<div class="page-stack">${pageTitle("HR and workload intelligence","Workforce analytics","Headcount, overtime, leave, task capacity, and model-predicted workload status.")}<div class="two-column">${panel("Headcount by department",barList(head,"department","count"))}${panel("Predicted workload status",barList(workload,"status","count"))}</div>${panel("Highest overtime employees",table(d.top_overtime,20),"Year-to-date overtime from the curated HR data")}</div>`;
  }

  async function salesPage(content) {
    const d=await get("/dashboard/sales");
    content.innerHTML=`<div class="page-stack">${pageTitle("Sales Analytics Agent","Sales performance","Revenue, profit, order volume, regions, categories, channels, and discount controls.")}<div class="two-column">${panel("Sales by region",barList(d.region,"region","sales_usd"))}${panel("Profit by category",barList(d.category,"product_category","profit_usd"))}</div>${panel("Regional detail",table(d.region))}${panel("Category detail",table(d.category))}</div>`;
  }

  async function documentsPage(content) {
    const docs=await get("/documents");
    content.innerHTML=`<div class="page-stack">${pageTitle("Secure RAG knowledge base","Enterprise documents","Canonical PDF/DOCX policies plus authorized uploads. Role and permission filters are enforced before retrieval.")}<div id="doc-message"></div>${panel("Publish an enterprise document",`<form id="doc-form" class="document-form"><label>File<input id="doc-file" type="file" accept=".pdf,.docx,.txt,.csv,.xlsx" required></label><label>Display title<input id="doc-title" placeholder="Optional"></label><label>Classification<select id="doc-class"><option>Internal</option><option>Confidential</option><option>Restricted</option></select></label><label>Required permission<input id="doc-permission" value="document.read_public"></label><label class="wide">Allowed roles<input id="doc-roles" value="Admin|Executive|HR_Manager|Project_Manager|Finance_Manager|Sales_Manager|Security_Officer|Employee|Auditor|AI_Reviewer"></label><button class="primary-button" id="doc-button">Upload and index</button></form>`,"Requires document.upload. Temporary chat attachments are session-only.")}${panel("Authorized document catalogue",table(docs,50),`${docs.length} documents visible to your role`)}</div>`;
    document.getElementById("doc-form").addEventListener("submit",uploadDoc);
  }
  async function uploadDoc(event) {
    event.preventDefault(); const file=document.getElementById("doc-file").files[0]; if(!file)return;
    const button=document.getElementById("doc-button"), msg=document.getElementById("doc-message");button.disabled=true;msg.innerHTML="";
    const form=new FormData();form.append("file",file);form.append("title",document.getElementById("doc-title").value||file.name);form.append("classification",document.getElementById("doc-class").value);form.append("allowed_roles",document.getElementById("doc-roles").value);form.append("required_permission",document.getElementById("doc-permission").value);
    try { const result=await request("/documents/upload",{method:"POST",body:form});msg.innerHTML=`<div class="success-box">Uploaded and indexed ${esc(result.title||file.name)}.</div>`;setTimeout(()=>documentsPage(document.getElementById("content")),500); } catch(e){msg.innerHTML=errorBox(e.message);} finally{button.disabled=false;}
  }

  async function approvalsPage(content) {
    const d=await get("/approvals"), records=[...d.runtime.map(x=>({...x,origin:"runtime"})),...d.dataset_pending];
    content.innerHTML=`<div class="page-stack">${pageTitle("Human-in-the-Loop gateway","Approval queue","User-requested sensitive actions remain paused until an authorized human decides.")}<div id="approval-message"></div>${records.length?`<div class="approval-grid">${records.map((r,i)=>panel(r.request_type||"Approval",`<div class="approval-detail"><div><span>Object</span><strong>${esc(r.business_object_id)}</strong></div><div><span>Risk tier</span><strong>${esc(r.risk_tier)}</strong></div><div><span>Action</span><strong>${esc(r.requested_action)}</strong></div><div><span>Required roles</span><strong>${esc(Array.isArray(r.required_roles)?r.required_roles.join(", "):r.required_approver_roles||"")}</strong></div></div>${jsonView(r.payload_json||r.action_payload_json||{})}${String(r.status)==="Pending"?`<div class="approval-actions"><button class="primary-button" data-decision="Approved" data-id="${esc(r.approval_id)}">Approve</button><button class="danger-button" data-decision="Rejected" data-id="${esc(r.approval_id)}">Reject</button></div>`:""}`,`${esc(r.approval_id)} · ${esc(r.origin||"dataset")}`,badge(r.status))).join("")}</div>`:`<div class="empty-state">No approval records are available.</div>`}</div>`;
    document.querySelectorAll("[data-decision]").forEach(button=>button.addEventListener("click",()=>decideApproval(button.dataset.id,button.dataset.decision)));
  }
  async function decideApproval(id,decision) { const msg=document.getElementById("approval-message"); try{await post(`/approvals/${id}/decision`,{decision,comment:`Decision entered from dashboard: ${decision}`});msg.innerHTML=`<div class="success-box">${esc(id)} was ${esc(decision.toLowerCase())}.</div>`;setTimeout(()=>approvalsPage(document.getElementById("content")),500);}catch(e){msg.innerHTML=errorBox(e.message);} }

  async function monitoringPage(content) {
    const d=await get("/dashboard/monitoring");
    const statuses=Object.entries(d.workflow_status_counts||{}).map(([status,count])=>({status,count}));
    const errors=Object.entries(d.judge_error_types||{}).map(([error_type,count])=>({error_type,count}));
    content.innerHTML=`<div class="page-stack">${pageTitle("Agent observability and evaluation","Reliability monitoring","Pass rate, review rate, hallucination, grounding, latency, disagreement, and regression indicators.")}<div class="stat-grid five">${stat("Pass Rate",`${(d.average_pass_rate*100).toFixed(1)}%`,"","good")}${stat("Review Rate",`${(d.average_review_rate*100).toFixed(1)}%`,"","warn")}${stat("Hallucination",`${(d.average_hallucination_rate*100).toFixed(1)}%`,"",d.average_hallucination_rate>.1?"danger":"good")}${stat("Average Latency",`${d.average_workflow_execution_ms.toFixed(0)} ms`)}${stat("Disagreement",`${(d.judge_human_disagreement_rate*100).toFixed(1)}%`)}</div><div class="two-column">${panel("Quality scores",`${progress(d.average_workflow_confidence*100,"Workflow confidence")}${progress(d.average_grounding_score*100,"Grounding score")}${progress((1-d.average_regression_rate)*100,"Regression-free rate")}`)}${panel("Workflow outcomes",barList(statuses,"status","count"))}</div><div class="two-column">${panel("Judge error categories",barList(errors,"error_type","count"))}${panel("Raw monitoring summary",jsonView(d))}</div></div>`;
  }

  async function modelsPage(content) {
    const models=await get("/models");
    content.innerHTML=`<div class="page-stack">${pageTitle("Training artifacts and metrics","Model center","Saved scikit-learn, RAG, and optional neural artifacts used by the enterprise agents.")}<div class="toolbar"><button id="reload-models" class="secondary-button">Reload model registry</button><span class="small-note">Use after retraining without restarting the API.</span></div><div id="model-message"></div><div class="model-grid">${models.map(m=>panel(humanize(m.model_name),`<div class="model-meta"><span>Artifact</span><strong>${esc(m.artifact_path)}</strong></div>${jsonView(m.metrics||{})}`,m.trained_at?`Trained ${m.trained_at}`:"Not trained",badge(m.available?"Available":"Missing",m.available?"good":"danger"))).join("")}</div></div>`;
    document.getElementById("reload-models").addEventListener("click",async()=>{const msg=document.getElementById("model-message");try{await request("/models/reload",{method:"POST"});msg.innerHTML='<div class="success-box">Model registry reloaded.</div>';setTimeout(()=>modelsPage(document.getElementById("content")),400);}catch(e){msg.innerHTML=errorBox(e.message);}});
  }

  async function auditPage(content) {
    const d=await get("/audit?limit=80");
    content.innerHTML=`<div class="page-stack">${pageTitle("Immutable evidence and live events","Audit logs","Authorization decisions, workflow runs, uploads, approvals, and historical enterprise events.")}<div class="two-column">${panel("Live runtime audit",table(d.runtime,80),`${d.runtime.length} recent events`)}${panel("Curated historical audit",table(d.dataset,80),`${d.dataset.length} sample events`)}</div></div>`;
  }

  async function start() {
    if (!API) {
      root.innerHTML = `<main class="center-screen"><section class="login-card"><div class="brand login-brand"><div class="brand-mark">NC</div><div><strong>NexaCore</strong><span>Enterprise AI Assistant</span></div></div><h1>Assistant service is not connected yet</h1><p>The dashboard has been published. Sign-in, document analysis, and AI responses will be available once the assistant service is connected.</p></section></main>`;
      return;
    }
    if (!state.token) return renderLogin();
    try { state.user=await get("/auth/me"); renderShell(); } catch { logout(); }
  }
  start();
})();
