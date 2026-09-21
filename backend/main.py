import os
import io
from typing import Any, Dict

# Fixed: explicit typing imports resolved the undefined Dict/Any runtime issues.
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.engine import process_evidence_df, extract_entities_and_relationships, evaluate_correlation_rules
from backend.graph_builder import build_cytoscape_graph
from backend.utils import calculate_sha256, generate_investigative_brief
from backend.models import AnalysisResponse

app = FastAPI(
    title="CYBERTRACE API",
    description="AI-Powered Unified Cyber Fraud Analysis & Digital Artifact Correlator",
    version="1.0.0"
)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "synthetic_evidence.csv")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Serve Frontend static assets
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def serve_index():
    """Serves main forensic investigation UI."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

def run_pipeline(csv_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Helper method executing full analysis pipeline."""
    sha256_hash = calculate_sha256(csv_bytes)
    
    df = pd.read_csv(io.BytesIO(csv_bytes))
    clean_df = process_evidence_df(df)
    
    entities, relationships, timeline = extract_entities_and_relationships(clean_df)
    risk_assessment = evaluate_correlation_rules(entities, relationships, clean_df)
    graph_data = build_cytoscape_graph(entities, relationships)

    top_entities = [e.value for e in entities if e.type in ['PHONE', 'IMEI', 'UPI']][:5]

    signals_dict = [s.model_dump() for s in risk_assessment.signals]
    brief = generate_investigative_brief(
        file_name=filename,
        record_count=len(clean_df),
        sha256_hash=sha256_hash,
        entities_count=len(entities),
        relationships_count=len(relationships),
        risk_score=risk_assessment.score,
        risk_level=risk_assessment.level,
        signals=signals_dict,
        top_entities=top_entities
    )

    return {
        "summary": {
            "file_name": filename,
            "record_count": len(clean_df),
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        },
        "entities": [e.model_dump() for e in entities],
        "relationships": [r.model_dump() for r in relationships],
        "risk": risk_assessment.model_dump(),
        "timeline": [t.model_dump() for t in timeline],
        "graph": graph_data,
        "sha256": sha256_hash,
        "investigative_brief": brief
    }

@app.get("/api/demo")
async def get_demo_analysis():
    """Instant execution route loading built-in synthetic evidence dataset."""
    if not os.path.exists(DATA_PATH):
        raise HTTPException(status_code=404, detail="Synthetic demo evidence file not found.")
    
    with open(DATA_PATH, "rb") as f:
        content = f.read()
    
    return run_pipeline(content, "synthetic_evidence.csv")

@app.post("/api/analyze")
async def analyze_uploaded_csv(file: UploadFile = File(...)):
    """CSV evidence upload endpoint."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV evidence files are supported.")
    
    content = await file.read()
    return run_pipeline(content, file.filename)