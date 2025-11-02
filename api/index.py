from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict
from supabase import create_client, Client
import os
from uuid import uuid4

# ---- Supabase setup ----
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Train.ai Tool API")
templates = Jinja2Templates(directory="templates")

# ---- Helper ----
def _get_flow(flow_id: str):
    res = supabase.table("flows").select("*").eq("id", flow_id).execute()
    return (res.data or [None])[0]

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
    action: str
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

# ---------- ENDPOINTS ----------
@app.get("/")
def home():
    return {"message": "Train.ai tool API running", "dashboard": "/dashboard"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    res = supabase.table("flows").select("id, app, task, confidence").order("created_at", desc=True).execute()
    rows = res.data or []
    return templates.TemplateResponse("flows.html", {"request": request, "flows": rows})

@app.get("/dashboard/{flow_id}", response_class=HTMLResponse)
def dashboard_detail(request: Request, flow_id: str):
    flow = _get_flow(flow_id)
    if not flow:
        return templates.TemplateResponse(
            "flow_detail.html",
            {"request": request, "flow": {"id": flow_id, "task": "not found", "confidence": 0}},
        )
    return templates.TemplateResponse("flow_detail.html", {"request": request, "flow": flow})

@app.post("/crawl", response_model=CrawlResult)
def crawl(url: str, depth: int = 1):
    return CrawlResult(
        url=url,
        routes=["/projects/ABC/issues", "/secure/CreateIssue!default.jspa"],
        selectors=["button:has-text('Create')", "input[name='summary']", "textarea[name='description']"],
        snippets=["Create", "Epic", "Summary", "Description"],
        screenshots=[]
    )

@app.get("/doc_search", response_model=DocSearchResponse)
def doc_search(query: str):
    return DocSearchResponse(
        results=[DocChunk(ref="pdf://jira_guide#p12", text="To create an Epic, click Create, choose Epic, and enter Summary...")]
    )

@app.get("/evaluate", response_model=EvaluateResponse)
def evaluate(selector: str, route: Optional[str] = None):
    ok = selector in ["button:has-text('Create')", "input[name='summary']", "textarea[name='description']"]
    return EvaluateResponse(valid=ok, notes="mock evaluation")

@app.post("/persist_flow")
def persist_flow(flow: Flow):
    flow_id = str(uuid4())
    data = flow.model_dump()
    data["id"] = flow_id
    supabase.table("flows").insert(data).execute()
    return {"status": "ok", "id": flow_id, "task": flow.task}

@app.get("/flows")
def list_flows():
    res = supabase.table("flows").select("id, app, task, confidence").order("created_at", desc=True).execute()
    return res.data or []

@app.get("/flows/{flow_id}")
def get_flow(flow_id: str):
    res = supabase.table("flows").select("*").eq("id", flow_id).execute()
    if not res.data:
        return {"error": "not found"}
    return res.data[0]
