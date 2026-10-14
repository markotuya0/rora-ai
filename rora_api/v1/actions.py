"""Approve endpoint — actions are suggestions until a human approves."""
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel

from rora_api.core.auth import verify_token, require_scope
from rora_api.core.rate_limit import check_rate_limit
from ops.audit import log_event, recent_events

router = APIRouter(prefix="/api/v1", tags=["v1-actions"])

approved_actions: list = []


class ApproveRequest(BaseModel):
    request_id: str
    action_key: str  # "email_draft" | "cs_tags" | "gtm_triggers"
    decision: str    # "approve" | "reject"


@router.post("/actions/approve")
def approve_action(body: ApproveRequest, req: Request):
    claims = verify_token(req.headers.get("authorization", "").removeprefix("Bearer ").strip())
    if not require_scope(claims, "approve:action"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope: approve:action")
    check_rate_limit(req)

    if body.decision not in ("approve", "reject"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="decision must be approve|reject")

    import api as app_module
    match = None
    for entry in app_module.query_history:
        if entry.get("request_id") == body.request_id and entry.get("actions"):
            match = entry
            break
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_id not found or has no actions")

    actions = match["actions"]
    if body.action_key not in ("email_draft", "cs_tags", "gtm_triggers"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown action_key")
    if body.action_key == "email_draft" and not actions.get("email_draft"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no email_draft for this request")

    actor = claims.get("sub", "unknown") if claims else "unknown"
    approved_actions.append({"request_id": body.request_id, "action_key": body.action_key, "decision": body.decision, "actor": actor})
    log_event(
        "action.approved" if body.decision == "approve" else "action.rejected",
        {"request_id": body.request_id, "action_key": body.action_key},
        actor=actor,
        request_id=body.request_id,
    )
    return {"status": "recorded", "decision": body.decision, "request_id": body.request_id, "action_key": body.action_key, "actor": actor}


@router.get("/actions/audit-log")
def audit_log(req: Request):
    claims = verify_token(req.headers.get("authorization", "").removeprefix("Bearer ").strip())
    if not require_scope(claims, "approve:action"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope: approve:action")
    check_rate_limit(req)
    return {"events": recent_events()}
