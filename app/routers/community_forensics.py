"""
Community Forensics Router — Premium feature for on-chain sleuths.

Endpoints:
- POST /api/v1/community-forensics/investigations — Create investigation
- GET  /api/v1/community-forensics/investigations — List community investigations
- GET  /api/v1/community-forensics/investigations/{id} — Get investigation detail
- POST /api/v1/community-forensics/investigations/{id}/evidence — Add evidence
- POST /api/v1/community-forensics/investigations/{id}/submit — Submit for review
- POST /api/v1/community-forensics/reports — Submit forensic report
- GET  /api/v1/community-forensics/reports — List verified reports
- GET  /api/v1/community-forensics/reports/{id} — Get report detail
- POST /api/v1/community-forensics/reports/{id}/verify — Verify report (admin)
- GET  /api/v1/community-forensics/leaderboard — Top sleuths
- GET  /api/v1/community-forensics/notebooks — List notebook templates
- GET  /api/v1/community-forensics/tools — List open-source tools
- POST /api/v1/community-forensics/blockscout/query — Proxy to Blockscout API
- GET  /api/v1/community-forensics/blockscout/health — Blockscout health
"""

from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime, timezone
import os
import httpx
import uuid
import json

router = APIRouter(prefix="/api/v1/community-forensics", tags=["community-forensics"])

# ── Config ──────────────────────────────────────────────────────

BLOCKSCOUT_URL = os.getenv("BLOCKSCOUT_URL", "http://rmi-blockscout:4000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ── Models ────────────────────────────────────────────────────────

class InvestigationCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    target_address: str = Field(..., min_length=20)
    chain: Literal["solana", "ethereum", "base", "bsc", "arbitrum", "polygon", "avalanche"]
    investigation_type: Literal["wallet_trace", "token_audit", "rug_pull", "social_engineering", "bundle_detection", "cross_chain"]
    tags: List[str] = Field(default_factory=list)

class EvidenceAdd(BaseModel):
    evidence_type: Literal["transaction", "screenshot", "contract_code", "social_post", "graph", "note", "external_link"]
    title: str
    content: str
    source_url: Optional[str] = None
    severity: Literal["info", "warning", "critical"] = "info"
    metadata: Optional[Dict] = None

class ReportSubmit(BaseModel):
    investigation_id: str
    title: str
    summary: str
    findings: List[Dict]
    risk_score: int = Field(..., ge=0, le=100)
    recommendations: List[str] = Field(default_factory=list)
    graph_data: Optional[Dict] = None  # Cytoscape/vis.js compatible graph

class VerifyReport(BaseModel):
    status: Literal["verified", "rejected", "needs_revision"]
    reviewer_notes: Optional[str] = None
    bounty_reward: Optional[int] = 0  # Reputation points

# ── In-memory store (replace with Supabase/PostgreSQL in prod) ──

INVESTIGATIONS: Dict[str, Dict] = {}
REPORTS: Dict[str, Dict] = {}
LEADERBOARD: Dict[str, Dict] = {}
NOTEBOOK_TEMPLATES = [
    {
        "id": "wallet-tracing-101",
        "name": "Wallet Tracing Fundamentals",
        "description": "Learn to trace fund flows using Web3.py and free APIs",
        "chain": "ethereum",
        "difficulty": "beginner",
        "tools": ["web3.py", "etherscan-api", "pandas", "networkx"],
        "download_url": "/static/notebooks/wallet_tracing_101.ipynb",
        "preview_image": "/static/notebooks/wallet_tracing_preview.png",
    },
    {
        "id": "solana-sleuth",
        "name": "Solana Sleuth Toolkit",
        "description": "Analyze Solana transactions, detect snipers, and map clusters",
        "chain": "solana",
        "difficulty": "intermediate",
        "tools": ["solana.py", "helius-api", "pandas", "matplotlib"],
        "download_url": "/static/notebooks/solana_sleuth.ipynb",
        "preview_image": "/static/notebooks/solana_sleuth_preview.png",
    },
    {
        "id": "bundle-detector",
        "name": "Bundle Detection Algorithm",
        "description": "Identify coordinated buy patterns and launch manipulation",
        "chain": "multi",
        "difficulty": "advanced",
        "tools": ["web3.py", "numpy", "scikit-learn", "graphviz"],
        "download_url": "/static/notebooks/bundle_detector.ipynb",
        "preview_image": "/static/notebooks/bundle_detector_preview.png",
    },
    {
        "id": "cross-chain-tracker",
        "name": "Cross-Chain Fund Tracker",
        "description": "Track stolen funds across bridges and mixers",
        "chain": "multi",
        "difficulty": "advanced",
        "tools": ["web3.py", "ccxt", "pandas", "networkx", "plotly"],
        "download_url": "/static/notebooks/cross_chain_tracker.ipynb",
        "preview_image": "/static/notebooks/cross_chain_tracker_preview.png",
    },
    {
        "id": "contract-audit",
        "name": "Smart Contract Audit Script",
        "description": "Automated vulnerability detection using Slither + Mythril",
        "chain": "ethereum",
        "difficulty": "advanced",
        "tools": ["slither-analyzer", "mythril", "solc", "pandas"],
        "download_url": "/static/notebooks/contract_audit.ipynb",
        "preview_image": "/static/notebooks/contract_audit_preview.png",
    },
    {
        "id": "social-manipulation",
        "name": "Social Manipulation Detector",
        "description": "Detect coordinated shilling and fake endorsements",
        "chain": "multi",
        "difficulty": "intermediate",
        "tools": ["tweepy", "praw", "pandas", "scikit-learn", "networkx"],
        "download_url": "/static/notebooks/social_manipulation.ipynb",
        "preview_image": "/static/notebooks/social_manipulation_preview.png",
    },
]

OPEN_SOURCE_TOOLS = [
    {
        "id": "blockscout",
        "name": "Blockscout Explorer",
        "description": "Self-hosted open-source blockchain explorer",
        "category": "explorer",
        "url": "/blockscout",
        "github": "https://github.com/blockscout/blockscout",
        "self_hosted": True,
        "chains": ["ethereum", "base", "bsc", "arbitrum", "polygon"],
    },
    {
        "id": "web3py",
        "name": "Web3.py",
        "description": "Python library for interacting with Ethereum",
        "category": "sdk",
        "url": "https://web3py.readthedocs.io",
        "github": "https://github.com/ethereum/web3.py",
        "self_hosted": False,
        "chains": ["ethereum", "base", "bsc", "arbitrum", "polygon"],
    },
    {
        "id": "solana-py",
        "name": "Solana.py",
        "description": "Python SDK for Solana blockchain",
        "category": "sdk",
        "url": "https://michaelhly.github.io/solana-py/",
        "github": "https://github.com/michaelhly/solana-py",
        "self_hosted": False,
        "chains": ["solana"],
    },
    {
        "id": "slither",
        "name": "Slither",
        "description": "Solidity static analysis framework",
        "category": "security",
        "url": "https://github.com/crytic/slither",
        "github": "https://github.com/crytic/slither",
        "self_hosted": False,
        "chains": ["ethereum", "base", "bsc", "arbitrum", "polygon"],
    },
    {
        "id": "mythril",
        "name": "Mythril",
        "description": "Security analysis tool for EVM bytecode",
        "category": "security",
        "url": "https://github.com/Consensys/mythril",
        "github": "https://github.com/Consensys/mythril",
        "self_hosted": False,
        "chains": ["ethereum", "base", "bsc", "arbitrum", "polygon"],
    },
    {
        "id": "helius",
        "name": "Helius API",
        "description": "Enhanced Solana APIs (free tier available)",
        "category": "api",
        "url": "https://helius.xyz",
        "github": None,
        "self_hosted": False,
        "chains": ["solana"],
    },
    {
        "id": "etherscan",
        "name": "Etherscan API",
        "description": "Ethereum blockchain explorer API",
        "category": "api",
        "url": "https://etherscan.io/apis",
        "github": None,
        "self_hosted": False,
        "chains": ["ethereum"],
    },
    {
        "id": "solscan",
        "name": "Solscan API",
        "description": "Solana explorer API for transaction data",
        "category": "api",
        "url": "https://solscan.io",
        "github": None,
        "self_hosted": False,
        "chains": ["solana"],
    },
    {
        "id": "networkx",
        "name": "NetworkX",
        "description": "Python graph library for transaction network analysis",
        "category": "analysis",
        "url": "https://networkx.org",
        "github": "https://github.com/networkx/networkx",
        "self_hosted": False,
        "chains": ["multi"],
    },
    {
        "id": "plotly",
        "name": "Plotly",
        "description": "Interactive visualization library for forensic graphs",
        "category": "visualization",
        "url": "https://plotly.com/python/",
        "github": "https://github.com/plotly/plotly.py",
        "self_hosted": False,
        "chains": ["multi"],
    },
]

# ── Helpers ───────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def gen_id() -> str:
    return str(uuid.uuid4())

def get_user_id(request) -> str:
    """Extract user ID from auth header. Fallback to anonymous."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        # In production, validate JWT here
        return auth.split(" ")[1][:32]  # Placeholder
    return "anonymous"

def update_reputation(user_id: str, points: int, action: str):
    """Update sleuth reputation score."""
    if user_id not in LEADERBOARD:
        LEADERBOARD[user_id] = {
            "user_id": user_id,
            "reputation": 0,
            "investigations": 0,
            "reports_submitted": 0,
            "reports_verified": 0,
            "evidence_added": 0,
            "joined_at": now_iso(),
        }
    LEADERBOARD[user_id]["reputation"] += points
    if action == "investigation":
        LEADERBOARD[user_id]["investigations"] += 1
    elif action == "report_submit":
        LEADERBOARD[user_id]["reports_submitted"] += 1
    elif action == "report_verified":
        LEADERBOARD[user_id]["reports_verified"] += 1
    elif action == "evidence":
        LEADERBOARD[user_id]["evidence_added"] += 1

# ── Endpoints: Investigations ────────────────────────────────────

@router.post("/investigations")
async def create_investigation(req: InvestigationCreate, request):
    """Create a new community investigation."""
    user_id = get_user_id(request)
    inv_id = gen_id()
    
    investigation = {
        "id": inv_id,
        "title": req.title,
        "description": req.description,
        "target_address": req.target_address,
        "chain": req.chain,
        "investigation_type": req.investigation_type,
        "tags": req.tags,
        "status": "open",  # open | in_progress | closed | submitted
        "created_by": user_id,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "evidence": [],
        "collaborators": [user_id],
        "report_id": None,
        "upvotes": 0,
        "views": 0,
    }
    INVESTIGATIONS[inv_id] = investigation
    update_reputation(user_id, 10, "investigation")
    
    return {"id": inv_id, "investigation": investigation}

@router.get("/investigations")
async def list_investigations(
    chain: Optional[str] = None,
    status: Optional[str] = None,
    investigation_type: Optional[str] = None,
    sort: Literal["newest", "popular", "trending"] = "newest",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List community investigations with filters."""
    results = list(INVESTIGATIONS.values())
    
    if chain:
        results = [r for r in results if r["chain"] == chain]
    if status:
        results = [r for r in results if r["status"] == status]
    if investigation_type:
        results = [r for r in results if r["investigation_type"] == investigation_type]
    
    if sort == "popular":
        results.sort(key=lambda x: x["upvotes"], reverse=True)
    elif sort == "trending":
        results.sort(key=lambda x: x["views"] + x["upvotes"] * 3, reverse=True)
    else:
        results.sort(key=lambda x: x["created_at"], reverse=True)
    
    total = len(results)
    results = results[offset:offset + limit]
    
    return {"investigations": results, "total": total, "limit": limit, "offset": offset}

@router.get("/investigations/{inv_id}")
async def get_investigation(inv_id: str):
    """Get investigation details with evidence."""
    if inv_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    inv = INVESTIGATIONS[inv_id]
    inv["views"] = inv.get("views", 0) + 1
    return inv

@router.post("/investigations/{inv_id}/evidence")
async def add_evidence(inv_id: str, req: EvidenceAdd, request):
    """Add evidence to an investigation."""
    if inv_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    user_id = get_user_id(request)
    evidence = {
        "id": gen_id(),
        "investigation_id": inv_id,
        "evidence_type": req.evidence_type,
        "title": req.title,
        "content": req.content,
        "source_url": req.source_url,
        "severity": req.severity,
        "metadata": req.metadata or {},
        "added_by": user_id,
        "added_at": now_iso(),
        "verified": False,
    }
    
    INVESTIGATIONS[inv_id]["evidence"].append(evidence)
    INVESTIGATIONS[inv_id]["updated_at"] = now_iso()
    update_reputation(user_id, 5, "evidence")
    
    return {"evidence_id": evidence["id"], "evidence": evidence}

@router.post("/investigations/{inv_id}/upvote")
async def upvote_investigation(inv_id: str, request):
    """Upvote an investigation."""
    if inv_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    INVESTIGATIONS[inv_id]["upvotes"] = INVESTIGATIONS[inv_id].get("upvotes", 0) + 1
    return {"upvotes": INVESTIGATIONS[inv_id]["upvotes"]}

@router.post("/investigations/{inv_id}/submit")
async def submit_investigation(inv_id: str, request):
    """Submit investigation for official review."""
    if inv_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    INVESTIGATIONS[inv_id]["status"] = "submitted"
    INVESTIGATIONS[inv_id]["updated_at"] = now_iso()
    
    return {"status": "submitted", "message": "Investigation submitted for review"}

# ── Endpoints: Reports ───────────────────────────────────────────

@router.post("/reports")
async def submit_report(req: ReportSubmit, request):
    """Submit a forensic report from community investigation."""
    user_id = get_user_id(request)
    report_id = gen_id()
    
    report = {
        "id": report_id,
        "investigation_id": req.investigation_id,
        "title": req.title,
        "summary": req.summary,
        "findings": req.findings,
        "risk_score": req.risk_score,
        "recommendations": req.recommendations,
        "graph_data": req.graph_data,
        "submitted_by": user_id,
        "submitted_at": now_iso(),
        "status": "pending",  # pending | verified | rejected | featured
        "reviewer_notes": None,
        "verified_by": None,
        "verified_at": None,
        "bounty_reward": 0,
        "upvotes": 0,
        "views": 0,
    }
    REPORTS[report_id] = report
    update_reputation(user_id, 25, "report_submit")
    
    # Link to investigation
    if req.investigation_id in INVESTIGATIONS:
        INVESTIGATIONS[req.investigation_id]["report_id"] = report_id
        INVESTIGATIONS[req.investigation_id]["status"] = "submitted"
    
    return {"id": report_id, "report": report}

@router.get("/reports")
async def list_reports(
    status: Optional[str] = None,
    chain: Optional[str] = None,
    sort: Literal["newest", "popular", "verified"] = "verified",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List community forensic reports."""
    results = list(REPORTS.values())
    
    if status:
        results = [r for r in results if r["status"] == status]
    
    if sort == "popular":
        results.sort(key=lambda x: x["upvotes"], reverse=True)
    elif sort == "newest":
        results.sort(key=lambda x: x["submitted_at"], reverse=True)
    else:  # verified first
        results.sort(key=lambda x: (x["status"] != "verified", -x["upvotes"]))
    
    total = len(results)
    results = results[offset:offset + limit]
    
    return {"reports": results, "total": total, "limit": limit, "offset": offset}

@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get report details."""
    if report_id not in REPORTS:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = REPORTS[report_id]
    report["views"] = report.get("views", 0) + 1
    return report

@router.post("/reports/{report_id}/verify")
async def verify_report(report_id: str, req: VerifyReport, request):
    """Verify a community report (admin only in production)."""
    if report_id not in REPORTS:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = REPORTS[report_id]
    report["status"] = req.status
    report["reviewer_notes"] = req.reviewer_notes
    report["bounty_reward"] = req.bounty_reward
    report["verified_at"] = now_iso()
    
    if req.status == "verified":
        update_reputation(report["submitted_by"], req.bounty_reward or 50, "report_verified")
    
    return {"report": report}

@router.post("/reports/{report_id}/upvote")
async def upvote_report(report_id: str, request):
    """Upvote a report."""
    if report_id not in REPORTS:
        raise HTTPException(status_code=404, detail="Report not found")
    
    REPORTS[report_id]["upvotes"] = REPORTS[report_id].get("upvotes", 0) + 1
    return {"upvotes": REPORTS[report_id]["upvotes"]}

# ── Endpoints: Leaderboard ───────────────────────────────────────

@router.get("/leaderboard")
async def get_leaderboard(
    period: Literal["all_time", "month", "week"] = "all_time",
    limit: int = Query(50, ge=1, le=100),
):
    """Get top community sleuths."""
    sleuths = list(LEADERBOARD.values())
    sleuths.sort(key=lambda x: x["reputation"], reverse=True)
    
    return {
        "sleuths": sleuths[:limit],
        "total_sleuths": len(sleuths),
        "your_rank": None,  # Would calculate based on auth
    }

# ── Endpoints: Notebooks & Tools ─────────────────────────────────

@router.get("/notebooks")
async def list_notebooks(
    chain: Optional[str] = None,
    difficulty: Optional[str] = None,
):
    """List Jupyter notebook templates for on-chain analysis."""
    results = NOTEBOOK_TEMPLATES
    
    if chain:
        results = [n for n in results if n["chain"] == chain or n["chain"] == "multi"]
    if difficulty:
        results = [n for n in results if n["difficulty"] == difficulty]
    
    return {"notebooks": results, "total": len(results)}

@router.get("/tools")
async def list_tools(
    chain: Optional[str] = None,
    category: Optional[str] = None,
):
    """List open-source tools for community forensics."""
    results = OPEN_SOURCE_TOOLS
    
    if chain:
        results = [t for t in results if chain in t["chains"] or "multi" in t["chains"]]
    if category:
        results = [t for t in results if t["category"] == category]
    
    return {"tools": results, "total": len(results)}

# ── Endpoints: Blockscout Proxy ──────────────────────────────────

@router.get("/blockscout/health")
async def blockscout_health():
    """Check Blockscout instance health."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BLOCKSCOUT_URL}/api/v2/main-page/indexing-status")
            return {"status": "ok", "blockscout": resp.json()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/blockscout/{path:path}")
async def blockscout_proxy(path: str, request):
    """Proxy requests to self-hosted Blockscout API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward query params
            query = str(request.query_params)
            url = f"{BLOCKSCOUT_URL}/api/v2/{path}"
            if query:
                url += f"?{query}"
            
            resp = await client.get(url)
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Blockscout unavailable: {e}")

# ── Endpoints: File Uploads ──────────────────────────────────────

@router.post("/investigations/{inv_id}/upload")
async def upload_evidence_file(inv_id: str, file: UploadFile, request):
    """Upload evidence file (screenshot, graph export, etc)."""
    if inv_id not in INVESTIGATIONS:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # In production: upload to S3/Cloudflare R2
    # For now, return metadata
    user_id = get_user_id(request)
    file_id = gen_id()
    
    evidence = {
        "id": file_id,
        "investigation_id": inv_id,
        "evidence_type": "screenshot" if file.content_type and "image" in file.content_type else "file",
        "title": file.filename,
        "content": f"Uploaded file: {file.filename} ({file.size} bytes)",
        "source_url": f"/uploads/{file_id}",
        "severity": "info",
        "metadata": {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file.size,
        },
        "added_by": user_id,
        "added_at": now_iso(),
        "verified": False,
    }
    
    INVESTIGATIONS[inv_id]["evidence"].append(evidence)
    INVESTIGATIONS[inv_id]["updated_at"] = now_iso()
    update_reputation(user_id, 5, "evidence")
    
    return {"file_id": file_id, "evidence": evidence}

# ── Endpoints: Stats ─────────────────────────────────────────────

@router.get("/stats")
async def community_stats():
    """Get community forensics platform statistics."""
    total_investigations = len(INVESTIGATIONS)
    total_reports = len(REPORTS)
    verified_reports = len([r for r in REPORTS.values() if r["status"] == "verified"])
    total_sleuths = len(LEADERBOARD)
    total_evidence = sum(len(inv["evidence"]) for inv in INVESTIGATIONS.values())
    
    return {
        "total_investigations": total_investigations,
        "total_reports": total_reports,
        "verified_reports": verified_reports,
        "verification_rate": round(verified_reports / total_reports * 100, 1) if total_reports else 0,
        "total_sleuths": total_sleuths,
        "total_evidence": total_evidence,
        "notebook_templates": len(NOTEBOOK_TEMPLATES),
        "open_source_tools": len(OPEN_SOURCE_TOOLS),
    }
