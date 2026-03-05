import React, { useState, useEffect, useRef, useCallback } from "react";
import "./App.css";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
const WS_URL = process.env.REACT_APP_WS_URL || "ws://localhost:8000";

const AGENT_META = {
  "Code Generator": {
    number: "01",
    color: "#1a3a5c",
    desc: "Writes production-ready Python code",
    idleIcon: "{ }",
  },
  "Test Writer": {
    number: "02",
    color: "#2d5a3d",
    desc: "Writes comprehensive pytest unit tests",
    idleIcon: "✓ ✗",
  },
  "Code Reviewer": {
    number: "03",
    color: "#5c3a1a",
    desc: "Reviews quality, security & performance",
    idleIcon: "⌥",
  },
};

function AgentCard({ agentName, status, output }) {
  const meta = AGENT_META[agentName] || {};
  const outputRef = useRef(null);

  useEffect(() => {
    if (outputRef.current && status === "running") {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output, status]);

  return (
    <div
      className={`agent-card ${status}`}
      style={{ "--agent-color": meta.color }}
    >
      <div className="agent-header">
        <div className="agent-number">AGENT {meta.number}</div>
        <div className="agent-name-row">
          <h3 className="agent-name">{agentName}</h3>
          <span className={`agent-status-pill ${status}`}>
            {status === "running" ? "● live" : status === "done" ? "✓ done" : "○ waiting"}
          </span>
        </div>
        <p className="agent-desc">{meta.desc}</p>
      </div>

      <div className="agent-output-wrap" ref={outputRef}>
        {output ? (
          <pre className="agent-output">{output}</pre>
        ) : (
          <div className="agent-placeholder">
            <span className="placeholder-icon">{meta.idleIcon}</span>
            <span className="placeholder-text">
              {status === "idle" ? "Waiting for previous agent" : "Generating..."}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [agents, setAgents] = useState({
    "Code Generator": { status: "idle", output: "" },
    "Test Writer": { status: "idle", output: "" },
    "Code Reviewer": { status: "idle", output: "" },
  });
  const [pipelineStatus, setPipelineStatus] = useState("idle");
  const [activeAgent, setActiveAgent] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const wsRef = useRef(null);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/sessions`);
      const data = await res.json();
      setHistory(data);
    } catch {}
  }, []);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const resetAgents = () => {
    setAgents({
      "Code Generator": { status: "idle", output: "" },
      "Test Writer": { status: "idle", output: "" },
      "Code Reviewer": { status: "idle", output: "" },
    });
    setActiveAgent(null);
  };

  const handleRun = async () => {
    if (!prompt.trim() || pipelineStatus === "running") return;
    resetAgents();
    setPipelineStatus("running");

    let sid;
    try {
      const res = await fetch(`${API_URL}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      sid = data.session_id;
      setSessionId(sid);
    } catch {
      setPipelineStatus("error");
      return;
    }

    const ws = new WebSocket(`${WS_URL}/api/ws/${sid}?prompt=${encodeURIComponent(prompt)}`);
    wsRef.current = ws;

    ws.onopen = () => console.log("WS connected");
    ws.onclose = (e) => console.log("WS closed", e.code);

    ws.onmessage = (evt) => {
      const event = JSON.parse(evt.data);
      if (event.type === "agent_start") {
        setActiveAgent(event.agent);
        setAgents(prev => ({ ...prev, [event.agent]: { status: "running", output: "" } }));
      } else if (event.type === "agent_chunk") {
        setAgents(prev => ({
          ...prev,
          [event.agent]: { ...prev[event.agent], output: prev[event.agent].output + event.chunk },
        }));
      } else if (event.type === "agent_done") {
        setAgents(prev => ({ ...prev, [event.agent]: { ...prev[event.agent], status: "done" } }));
        setActiveAgent(null);
      } else if (event.type === "pipeline_complete") {
        setPipelineStatus("done");
        fetchHistory();
        ws.close();
      } else if (event.type === "error") {
        setPipelineStatus("error");
        ws.close();
      }
    };

    ws.onerror = () => setPipelineStatus("error");
  };

  const handleLoadHistory = async (session) => {
    setShowHistory(false);
    try {
      const res = await fetch(`${API_URL}/api/sessions/${session.session_id}`);
      const data = await res.json();
      const agentMap = { code_generator: "Code Generator", test_writer: "Test Writer", code_reviewer: "Code Reviewer" };
      const newAgents = {
        "Code Generator": { status: "idle", output: "" },
        "Test Writer": { status: "idle", output: "" },
        "Code Reviewer": { status: "idle", output: "" },
      };
      data.agents.forEach(a => {
        const name = agentMap[a.agent_name];
        if (name) newAgents[name] = { status: "done", output: a.output || "" };
      });
      setAgents(newAgents);
      setPrompt(data.prompt);
      setPipelineStatus("done");
      setSessionId(data.session_id);
    } catch {}
  };

  const today = new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });

  return (
    <div className="app">
      {/* Masthead */}
      <header className="masthead">
        <div className="masthead-left">
          <div className="issue-badge">
            <div>{today}</div>
            <div>LangGraph · FastAPI · Groq</div>
          </div>
        </div>

        <div className="masthead-center">
          <h1 className="masthead-title">Agent<span>Forge</span></h1>
          <p className="masthead-sub">Multi-Agent Development Assistant</p>
        </div>

        <div className="masthead-right">
          <button className="nav-btn" onClick={() => setShowHistory(!showHistory)}>
            Archive
          </button>
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer" className="nav-btn">
            API ↗
          </a>
        </div>
      </header>
      <div className="rule-thin" />

      {/* History */}
      {showHistory && (
        <div className="history-panel">
          <h4>Session Archive</h4>
          {history.length === 0 ? (
            <p className="no-history">No sessions recorded yet.</p>
          ) : (
            <div className="history-list">
              {history.map((s, i) => (
                <button key={s.session_id} className="history-item" onClick={() => handleLoadHistory(s)}>
                  <span className="history-num">{String(i + 1).padStart(2, "0")}</span>
                  <span className="history-prompt">{s.prompt.slice(0, 60)}{s.prompt.length > 60 ? "…" : ""}</span>
                  <span className="history-status">{s.status}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <main className="main">
        {/* Prompt + sidebar */}
        <section className="prompt-section">
          <div className="prompt-left">
            <div className="prompt-eyebrow">New Request</div>
            <h2 className="prompt-headline">What would you like to build?</h2>
            <textarea
              className="prompt-textarea"
              placeholder="e.g. Write a function that finds all pairs of integers in a list that sum to a target value..."
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              rows={4}
              onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleRun(); }}
            />
            <p className="prompt-hint">⌘↵ to run</p>
          </div>

          <div className="prompt-right">
            <button
              className={`run-btn ${pipelineStatus === "running" ? "running" : ""}`}
              onClick={handleRun}
              disabled={!prompt.trim() || pipelineStatus === "running"}
            >
              {pipelineStatus === "running"
                ? <><span className="spinner" /> Processing</>
                : "Run Pipeline →"
              }
            </button>

            <div className="pipeline-info">
              <strong>Pipeline</strong>
              01 Code Generator<br />
              02 Test Writer<br />
              03 Code Reviewer
              {activeAgent && <><br /><br />▶ {activeAgent}...</>}
            </div>
          </div>
        </section>

        {/* Status bar */}
        {pipelineStatus !== "idle" && (
          <div className={`status-bar ${pipelineStatus}`}>
            <span className="status-dot" />
            {pipelineStatus === "running" && `Running — ${activeAgent || "initializing"}...`}
            {pipelineStatus === "done" && "All agents completed successfully"}
            {pipelineStatus === "error" && "Pipeline error — check your Groq API key and try again"}
            {sessionId && pipelineStatus === "done" && (
              <span className="status-session">#{sessionId.slice(0, 8)}</span>
            )}
          </div>
        )}

        {/* Agent columns */}
        <section className="agents-section">
          <div className="section-rule">
            <span className="section-rule-label">Agent Output</span>
            <span className="section-rule-line" />
          </div>

          <div className="agents-grid">
            {Object.entries(agents).map(([name, state]) => (
              <AgentCard
                key={name}
                agentName={name}
                status={state.status}
                output={state.output}
              />
            ))}
          </div>
        </section>
      </main>

      <footer className="footer">
        <span className="footer-left">
          FastAPI · LangGraph · React · PostgreSQL · Docker · Groq LLaMA-3.3
        </span>
        <span className="footer-right">AgentForge</span>
      </footer>
    </div>
  );
}