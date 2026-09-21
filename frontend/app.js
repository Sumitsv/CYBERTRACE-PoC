let cy = null;

document.addEventListener("DOMContentLoaded", () => {
  initCytoscape();
  document
    .getElementById("load-demo-btn")
    .addEventListener("click", loadDemoData);
  document.getElementById("file-upload").addEventListener("change", uploadCSV);
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
          color: "#f8fafc",
          "font-size": "9px",
          "font-family": "monospace",
          "text-valign": "bottom",
          "text-margin-y": 4,
          width: "28px",
          height: "28px",
          "border-width": 2,
          "border-color": "#0f172a",
        },
      },
      {
        selector: "edge",
        style: {
          width: 1.5,
          "line-color": "#334155",
          "curve-style": "bezier",
          opacity: 0.7,
        },
      },
      {
        selector: "edge[?is_suspicious]",
        style: {
          width: 2.5,
          "line-color": "#ef4444",
          "line-style": "dashed",
          opacity: 1.0,
        },
      },
    ],
    layout: { name: "grid" },
  });
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
  document.getElementById("stat-records").innerText = data.summary.record_count;
  document.getElementById("stat-entities").innerText =
    data.summary.entity_count;
  document.getElementById("stat-relationships").innerText =
    data.summary.relationship_count;

  const scoreElem = document.getElementById("stat-risk-score");
  const badgeElem = document.getElementById("risk-badge");
  scoreElem.innerText = `${data.risk.score}/100`;

  if (data.risk.score >= 70) {
    scoreElem.className = "text-2xl font-bold text-red-500";
    badgeElem.className =
      "text-xs px-2 py-1 rounded bg-red-950 border border-red-800 text-red-300 font-bold";
    badgeElem.innerText = "ILLUSTRATIVE HIGH RISK";
  } else if (data.risk.score >= 40) {
    scoreElem.className = "text-2xl font-bold text-amber-500";
    badgeElem.className =
      "text-xs px-2 py-1 rounded bg-amber-950 border border-amber-800 text-amber-300 font-bold";
    badgeElem.innerText = "ILLUSTRATIVE MEDIUM RISK";
  } else {
    scoreElem.className = "text-2xl font-bold text-emerald-400";
    badgeElem.className =
      "text-xs px-2 py-1 rounded bg-emerald-950 border border-emerald-800 text-emerald-300";
    badgeElem.innerText = "ILLUSTRATIVE LOW RISK";
  }

  const signalsContainer = document.getElementById("signals-list");
  signalsContainer.innerHTML = "";

  if (data.risk.signals.length === 0) {
    signalsContainer.innerHTML =
      '<p class="text-xs text-slate-500">No risk signals triggered.</p>';
  } else {
    data.risk.signals.forEach((sig) => {
      const card = document.createElement("div");
      card.className =
        "bg-slate-950 border border-slate-800 rounded p-3 text-xs";
      card.innerHTML = `
                <div class="flex justify-between items-center mb-1">
                    <span class="font-bold text-amber-400">${sig.name}</span>
                    <span class="text-[10px] bg-red-950 text-red-400 border border-red-900 px-1.5 py-0.5 rounded">+${sig.weight} PTS</span>
                </div>
                <p class="text-slate-400 text-[11px]">${sig.description}</p>
            `;
      signalsContainer.appendChild(card);
    });
  }

  document.getElementById("sha-file").innerText = data.summary.file_name;
  document.getElementById("sha-hash").innerText = data.sha256;

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

  const timelineContainer = document.getElementById("timeline-container");
  timelineContainer.innerHTML = "";
  data.timeline.forEach((event) => {
    const item = document.createElement("div");
    item.className = "timeline-item";
    item.innerHTML = `
            <div class="text-[10px] text-cyan-400 font-semibold">${event.timestamp} [${event.source}]</div>
            <div class="text-slate-200 text-xs">${event.event_type} &mdash; <span class="text-slate-400">${event.description}</span></div>
        `;
    timelineContainer.appendChild(item);
  });

  document.getElementById("brief-text").value = data.investigative_brief;
}
