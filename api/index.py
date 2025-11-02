from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict
from uuid import uuid4

app = FastAPI(title="Train.ai Tool API")

# ---------- MODELS ----------
class CrawlResult(BaseModel):
    url: str
    routes: List[str]
    selectors: List[str]
    snippets: List[str]
    screenshots: List[str] = []

class DocChunk(BaseModel):
    ref: str
    text: str

class DocSearchResponse(BaseModel):
    results: List[DocChunk]

class EvaluateResponse(BaseModel):
    valid: bool
    notes: Optional[str] = None

class FlowStep(BaseModel):
    selector: str
    action: str  # "click" | "type" | "select"
    value: Optional[str] = None
    assert_: Optional[str] = None

class Flow(BaseModel):
    app: str
    task: str
    confidence: float
    sources: List[Dict]
    steps: List[FlowStep]
    fallbacks: Dict
    role: List[str]
    prerequisites: List[str]

# ---------- IN-MEMORY STORE ----------
FLOWS: Dict[str, Dict] = {}  # id -> flow dict

# ---------- ENDPOINTS ----------
@app.get("/")
def home():
    return {"message": "Train.ai tool API running", "docs": "/openapi.json", "flows": "/flows"}

@app.post("/crawl", response_model=CrawlResult)
def crawl(url: str, depth: int = 1):
    # MOCK response for Jira "Create Epic"
    return CrawlResult(
        url=url,
        routes=["/projects/ABC/issues", "/secure/CreateIssue!default.jspa"],
        selectors=[
            "button:has-text('Create')",
            "input[name='summary']",
            "textarea[name='description']"
        ],
        snippets=["Create", "Epic", "Summary", "Description"],
        screenshots=[]
    )

@app.get("/doc_search", response_model=DocSearchResponse)
def doc_search(query: str):
    # MOCK doc result
    return DocSearchResponse(results=[
        DocChunk(
            ref="pdf://jira_guide#p12",
            text="To create an Epic, click Create, choose Epic, and enter Summary..."
        )
    ])

@app.get("/evaluate", response_model=EvaluateResponse)
def evaluate(selector: str, route: Optional[str] = None):
    ok = selector in [
        "button:has-text('Create')",
        "input[name='summary']",
        "textarea[name='description']"
    ]
    return EvaluateResponse(valid=ok, notes="mock evaluation")

@app.post("/persist_flow")
def persist_flow(flow: Flow):
    flow_id = str(uuid4())[:8]
    data = flow.model_dump()
    data["id"] = flow_id
    FLOWS[flow_id] = data
    return {"status": "ok", "id": flow_id, "task": flow.task}

# ---- NEW ADMIN ENDPOINTS ----
@app.get("/flows")
def list_flows():
    # Light summary list
    return [
        {"id": fid, "app": f["app"], "task": f["task"], "confidence": f["confidence"]}
        for fid, f in FLOWS.items()
    ]

@app.get("/flows/{flow_id}")
def get_flow(flow_id: str):
    if flow_id not in FLOWS:
        return {"error": "not found"}
    return FLOWS[flow_id]
