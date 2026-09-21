let cy = null;

const RISK_STYLES = {
  high: {
    badge: "HIGH-RISK PATTERN",
    className: "high",
    text: "Elevated risk based on configured heuristic signals.",
    color: "#f97316",
  },
  medium: {
    badge: "MEDIUM-RISK PATTERN",
    className: "medium",
    text: "Moderate correlation exposure based on current evidence.",
    color: "#fbbf24",
  },
  low: {
    badge: "LOW-RISK PATTERN",
    className: "low",
    text: "No immediate escalation indicated by the active rule set.",
    color: "#34d399",
  },
};

document.addEventListener("DOMContentLoaded", () => {
  initCytoscape();
  document
    .getElementById("load-demo-btn")
    .addEventListener("click", loadDemoData);
  document.getElementById("file-upload").addEventListener("change", uploadCSV);
  renderDashboardPlaceholder();
});

function initCytoscape() {
  cy = cytoscape({
    container: document.getElementById("cy"),
    style: [
      {
        selector: "node",
        style: {
          "background-color": "data(color)",
          label: "data(label)",
          color: "#e2e8f0",
          "font-size": "9px",
          "font-family": "Inter, ui-monospace, SFMono-Regular, monospace",
          "text-valign": "bottom",
          "text-margin-y": 6,
          width: "28px",
          height: "28px",
          "border-width": 2,
          "border-color": "#0f172a",
          "text-wrap": "wrap",
          "text-max-width": "90px",
          "overlay-padding": 8,
        },
      },
      {
        selector: "edge",
        style: {
          width: 1.4,
          "line-color": "#475569",
          "curve-style": "bezier",
          opacity: 0.8,
          "target-arrow-shape": "none",
        },
      },
      {
        selector: "edge[?is_suspicious]",
        style: {
          width: 2.2,
          "line-color": "#ef4444",
          "line-style": "dashed",
          opacity: 1,
        },
      },
    ],
    layout: { name: "grid" },
  });
}

function renderDashboardPlaceholder() {
  const signalsContainer = document.getElementById("signals-list");
  signalsContainer.innerHTML =
    '<div class="signal-empty">Click “Load Synthetic Evidence” to run the correlation engine.</div>';

  const timelineContainer = document.getElementById("timeline-container");
  timelineContainer.innerHTML =
    '<div class="timeline-empty">No timeline populated.</div>';

  const briefText = document.getElementById("brief-text");
  briefText.value = "Awaiting analysis output...";
}

function updateRiskUI(score) {
  const ring = document.getElementById("risk-ring");
  const scoreElem = document.getElementById("stat-risk-score");
  const badgeElem = document.getElementById("risk-badge");
  const summaryElem = document.getElementById("risk-summary");

  scoreElem.textContent = `${score} / 100`;

  let state = RISK_STYLES.low;
  if (score >= 70) state = RISK_STYLES.high;
  else if (score >= 40) state = RISK_STYLES.medium;

  ring.className = `risk-ring ${state.className}`;
  ring.style.background = `conic-gradient(${state.color} ${score}%, rgba(148, 163, 184, 0.18) 0)`;
  badgeElem.className = `risk-badge ${state.className}`;
  badgeElem.textContent = state.badge;
  summaryElem.textContent = state.text;
}

async function loadDemoData() {
  try {
    const res = await fetch("/api/demo");
    if (!res.ok) throw new Error("Failed to load demo payload.");
    const data = await res.json();
    renderDashboard(data);
  } catch (err) {
    alert("Error loading demo evidence: " + err.message);
  }
}

async function uploadCSV(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("CSV analysis failed.");
    const data = await res.json();
    renderDashboard(data);
  } catch (err) {
    alert("Upload error: " + err.message);
  }
}

function renderDashboard(data) {
  document.getElementById("stat-records").textContent =
    data.summary.record_count;
  document.getElementById("stat-entities").textContent =
    data.summary.entity_count;
  document.getElementById("stat-relationships").textContent =
    data.summary.relationship_count;

  updateRiskUI(data.risk.score);

  const signalsContainer = document.getElementById("signals-list");
  signalsContainer.innerHTML = "";

  if (!data.risk.signals || data.risk.signals.length === 0) {
    signalsContainer.innerHTML =
      '<div class="signal-empty">No active heuristic signals were triggered for this dataset.</div>';
  } else {
    data.risk.signals.forEach((sig) => {
      const card = document.createElement("div");
      card.className = "signal-card";
      card.innerHTML = `
        <div class="signal-header">
          <span class="signal-name">${sig.name}</span>
          <span class="signal-score">+${sig.weight}</span>
        </div>
        <div class="signal-meta">Rule-based / Explainable</div>
        <p>${sig.description}</p>
      `;
      signalsContainer.appendChild(card);
    });
  }

  document.getElementById("sha-file").textContent = data.summary.file_name;
  document.getElementById("sha-hash").textContent = data.sha256;

  if (cy) {
    cy.elements().remove();
    cy.add(data.graph.nodes);
    cy.add(data.graph.edges);

    const layout = cy.layout({
      name: "cose",
      animate: false,
      padding: 30,
      nodeRepulsion: 8000,
      idealEdgeLength: 50,
    });
    layout.run();
    cy.fit();
  }

  const timelineContainer = document.getElementById("timeline-container");
  timelineContainer.innerHTML = "";

  if (!data.timeline || data.timeline.length === 0) {
    timelineContainer.innerHTML =
      '<div class="timeline-empty">No timeline populated.</div>';
  } else {
    data.timeline.forEach((event) => {
      const item = document.createElement("div");
      item.className = "timeline-item";
      item.innerHTML = `
        <div class="timeline-head">
          <span class="timeline-time">${event.timestamp}</span>
          <span class="timeline-source">${event.source}</span>
          <span class="timeline-evidence">${event.evidence_id}</span>
        </div>
        <div class="timeline-event">${event.event_type}</div>
        <div class="timeline-description">${event.description}</div>
      `;
      timelineContainer.appendChild(item);
    });
  }

  document.getElementById("brief-text").value = data.investigative_brief;
}
