"use client";

import { useState } from "react";

const tasks = {
  Backlog: ["Survey instrument design & pilot", "Literature review: carbon pricing impacts", "Acquire state-level policy datasets", "Define treatment & control groups"],
  "In Progress": ["Clean & harmonize emissions data (2000–2023)", "Construct policy timeline and exposure index", "Difference-in-Differences model (baseline)", "Robustness checks & sensitivity analysis"],
  "In Review": ["Data quality summary & missingness report", "Model results review & validation", "Draft results section (working paper)"],
  Done: ["Research plan & scope definition", "IRB approval", "Collect energy price data (EIA)", "Assemble socio-economic covariates"],
};

export default function Home() {
  const [activeTab, setActiveTab] = useState("Board");
  const [query, setQuery] = useState("");
  const [sent, setSent] = useState(false);
  const [showTask, setShowTask] = useState(false);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">✣</span>Research<span>HUB</span></div>
        <div className="workspace-select"><small>WORKSPACE</small><b>Global Research Lab</b><span>⌄</span></div>
        <nav className="main-nav">{["Home", "My Work", "Activity", "Search"].map((item) => <button key={item}>{item}</button>)}</nav>
        <div className="section-label">PROJECTS <span>＋</span></div>
        <div className="project-list"><button className="selected"><i />Climate Policy Impact Evaluation</button>{["Urban Heat & Health Study", "Renewable Energy Transitions", "Biodiversity Monitoring"].map((item) => <button key={item}><i />{item}</button>)}</div>
        <div className="section-label">DATA & RESOURCES</div>
        <nav className="main-nav compact">{["Datasets", "Collections", "Code Repos", "Methods Library"].map((item) => <button key={item}>{item}</button>)}</nav>
        <div className="section-label">ADMIN</div>
        <nav className="main-nav compact">{["Team", "Permissions", "Integrations", "Audit Log"].map((item) => <button key={item}>{item}</button>)}</nav>
        <div className="profile"><div className="avatar maya">MC</div><div><b>Dr. Maya Chen</b><small>Principal Investigator</small></div><span>⌄</span></div>
      </aside>

      <section className="content">
        <header className="topbar"><div><small>PROJECT</small><h1>Climate Policy Impact Evaluation <span>⌄</span></h1></div><div className="top-actions"><span className="status">● On Track</span><div className="avatars"><span>MC</span><span>AP</span><span>JR</span><span>KS</span><em>+3</em></div><button className="share">Share</button><button className="icon-btn">⋮</button></div></header>
        <div className="tabs">{["Overview", "Board", "Files", "Datasets", "Reports", "Settings"].map((tab) => <button className={activeTab === tab ? "active" : ""} key={tab} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>

        <div className="toolbar"><button onClick={() => setActiveTab("Board")}>▣ &nbsp;Board⌄</button><button>By Workflow⌄</button><button>All Tasks⌄</button><button>≡ Filters⌄</button><span /><label>Dependencies <input type="checkbox" defaultChecked /></label><button>Group: None⌄</button><button>↗</button></div>
        <div className="workspace-grid">
          <div className="board-area"><div className="board-columns">{Object.entries(tasks).map(([column, items]) => <div className="column" key={column}><div className="column-title"><b>{column}</b><small>{items.length + (column === "Done" ? 8 : column === "Backlog" ? 4 : 1)}</small><span>…</span></div>{items.map((task, i) => <article className="task-card" key={task}><strong>{task}</strong><small>{column === "Done" ? "Completed" : i % 2 ? "ANALYSIS" : "DATA"}</small><div className="task-meta"><span className={i % 3 === 0 ? "avatar amber" : "avatar blue"}>{["AP", "JR", "MC", "KS"][i]}</span><span>{["A. Patel", "J. Rivera", "M. Chen", "K. Shah"][i]}</span><em>{column !== "Done" && `${30 + i * 10}%`}</em></div>{column === "In Progress" && <div className="progress"><i style={{ width: `${30 + i * 10}%` }} /></div>}</article>)}<button className="add-task" onClick={() => setShowTask(true)}>＋ Add task</button></div>)}</div></div>
          <aside className="right-rail"><Panel title="Activity" link="View all"><Activity /></Panel><Panel title="Team Conversation" link="⌄"><div className="channel"># cpie-research <span>⚑　♙ 6　⋮</span></div><Chat /></Panel></aside>
        </div>
        <section className="copilot"><div className="copilot-head"><b>AI Copilot <small>BETA</small></b><button>Ask</button><button>Write</button><button>Analyze</button><button>Summarize</button><span>Context: This project⌄　⌃</span></div><form onSubmit={(e) => { e.preventDefault(); setSent(true); }}><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask anything about your research..." /><button>➤</button></form><div className="suggestions"><button onClick={() => setQuery("Summarize open tasks and key blockers")}>Summarize open tasks and key blockers</button><button onClick={() => setQuery("What are my critical path dependencies?")}>What are my critical path dependencies?</button><button onClick={() => setQuery("Draft a methods section outline")}>Draft a methods section outline</button><button onClick={() => setQuery("Find relevant papers on carbon pricing")}>Find relevant papers on carbon pricing</button></div>{sent && <p className="copilot-response">I&apos;ll review the project context and prepare a concise answer for <b>{query || "your question"}</b>.</p>}</section>
      </section>
      {showTask && <div className="modal-backdrop"><div className="modal"><button className="close" onClick={() => setShowTask(false)}>×</button><small>NEW TASK</small><h2>Create a research task</h2><input placeholder="Task title" autoFocus /><textarea placeholder="Add context, links, or acceptance criteria" /><button className="share" onClick={() => setShowTask(false)}>Create task</button></div></div>}
    </main>
  );
}

function Panel({ title, link, children }: { title: string; link: string; children: React.ReactNode }) { return <section className="rail-panel"><header><h2>{title}</h2><a>{link}</a></header>{children}</section>; }
function Activity() { return <div className="activity">{["J. Rivera completed Clean & harmonize emissions data (2000–2023)", "K. Shah moved Model results review & validation to In Review", "A. Patel commented on Draft results section (working paper)", "T. Okafor uploaded Robustness checks results.csv"].map((text, i) => <p key={text}><b>{["✓", "→", "▣", "↗"][i]}</b><span>{text}</span><small>{i + 2}h ago</small></p>)}</div>; }
function Chat() { return <div className="chat">{[["Kavya Shah", "Just flagged CP-30 for review. The model diagnostics look good overall, but check the pre-trend plot in the appendix."], ["Miguel Rivera", "Thanks! Also added the updated emissions data through 2023."], ["Aisha Patel", "I&apos;ll draft the results section once CP-30 is approved."]].map(([name, text], i) => <p key={name}><span className={`avatar ${i === 1 ? "amber" : "blue"}`}>{name.split(" ").map((n) => n[0]).join("")}</span><span><b>{name}</b><small>9:{18 + i * 7} AM</small>{text}</span></p>)}<form><input placeholder="Message #cpie-research" /><button>➤</button></form></div>; }
