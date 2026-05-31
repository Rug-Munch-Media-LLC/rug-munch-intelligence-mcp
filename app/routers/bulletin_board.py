"""
RMI Bulletin Board API Router
===============================
Full REST API for bulletin board management.

Public endpoints (no auth):
  GET /api/v1/bulletin/posts          — List published posts
  GET /api/v1/bulletin/posts/{slug}  — Get single post by slug
  GET /api/v1/bulletin/categories    — List categories

Admin endpoints (require admin session):
  POST /api/v1/admin/bulletin/posts           — Create post
  PUT /api/v1/admin/bulletin/posts/{id}       — Update post
  DELETE /api/v1/admin/bulletin/posts/{id}    — Delete (archive) post
  GET /api/v1/admin/bulletin/posts            — List all posts (admin view)
  POST /api/v1/admin/bulletin/posts/{id}/publish   — Publish post
  POST /api/v1/admin/bulletin/posts/{id}/unpublish — Unpublish post
  POST /api/v1/admin/bulletin/posts/{id}/pin       — Pin/unpin post
  GET /api/v1/admin/bulletin/stats           — Board statistics
  GET /api/v1/admin/bulletin/scheduled       — List scheduled posts
  POST /api/v1/admin/bulletin/process-scheduled — Process scheduled posts
  POST /api/v1/admin/bulletin/process-expired — Archive expired posts
"""

import os
import json
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Body, Query
from pydantic import BaseModel, Field

from app.bulletin_board import (
    BulletinBoardManager, PostStatus, PostCategory,
    TargetAudience, Priority, ContentSanitizer,
)
from app.admin_backend import require_admin, AuditLogger

router = APIRouter(tags=["bulletin-board"])

# ── Public Endpoints ──────────────────────────────────────────

@router.get("/api/v1/bulletin/posts")
async def public_list_posts(
    request: Request,
    category: str = "",
    search: str = "",
    tag: str = "",
    limit: int = 20,
    offset: int = 0,
):
    """List published posts (public)."""
    tags = [tag] if tag else None
    result = await BulletinBoardManager.list_posts(
        category=category or None,
        status="published",
        search_query=search or None,
        tags=tags,
        limit=limit,
        offset=offset,
        sort_by="published_at",
        sort_order="desc",
    )
    
    # Return public-safe versions
    posts = []
    for p in result["posts"]:
        # Remove internal fields
        safe = {k: v for k, v in p.items() if k not in [
            "author_id", "author_email", "edit_history", "approved_by",
            "notification_sent", "version"
        ]}
        posts.append(safe)
    
    return {
        "posts": posts,
        "total": result["total"],
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/v1/bulletin/posts/{slug}")
async def public_get_post(request: Request, slug: str):
    """Get a single published post by slug (public)."""
    post = await BulletinBoardManager.get_post_by_slug(slug)
    if not post or post.status != PostStatus.PUBLISHED.value:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Track view
    await BulletinBoardManager.track_engagement(post.post_id, "view")
    
    return {"post": post.to_public_dict()}


@router.get("/api/v1/bulletin/categories")
async def public_categories():
    """List all categories with counts."""
    stats = await BulletinBoardManager.get_stats()
    categories = []
    for cat in PostCategory:
        categories.append({
            "id": cat.value,
            "name": cat.value.replace("_", " ").title(),
            "count": stats["categories"].get(cat.value, 0),
        })
    return {"categories": categories}


@router.get("/api/v1/bulletin/pinned")
async def public_pinned_posts(limit: int = 5):
    """Get pinned posts (public)."""
    result = await BulletinBoardManager.list_posts(
        pinned_only=True,
        status="published",
        limit=limit,
    )
    posts = []
    for p in result["posts"]:
        safe = {k: v for k, v in p.items() if k not in [
            "author_id", "author_email", "edit_history", "approved_by",
            "notification_sent", "version"
        ]}
        posts.append(safe)
    return {"posts": posts, "total": result["total"]}


# ── Admin Models ──────────────────────────────────────────────

class CreatePostRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = "news"
    priority: str = "normal"
    target_audience: str = "all"
    status: str = "draft"
    featured_image: str = ""
    attachments: List[dict] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    scheduled_at: Optional[str] = None
    expires_at: Optional[str] = None
    pinned: bool = False
    allow_comments: bool = False
    meta_title: str = ""
    meta_description: str = ""
    og_image: str = ""


class UpdatePostRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    target_audience: Optional[str] = None
    status: Optional[str] = None
    featured_image: Optional[str] = None
    attachments: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    scheduled_at: Optional[str] = None
    expires_at: Optional[str] = None
    pinned: Optional[bool] = None
    allow_comments: Optional[bool] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image: Optional[str] = None


class CommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[str] = None


# ── Admin Endpoints ───────────────────────────────────────────

@router.get("/api/v1/admin/bulletin/posts")
async def admin_list_posts(
    request: Request,
    category: str = "",
    status: str = "",
    search: str = "",
    pinned: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """List all posts (admin view with full data)."""
    auth = await require_admin(request, "content.read")
    admin = auth["admin"]
    
    result = await BulletinBoardManager.list_posts(
        category=category or None,
        status=status or None,
        search_query=search or None,
        pinned_only=pinned if pinned is not None else False,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    return {
        "posts": result["posts"],
        "total": result["total"],
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/v1/admin/bulletin/posts")
async def admin_create_post(request: Request, body: CreatePostRequest):
    """Create a new bulletin board post."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    
    # Validate category
    if body.category not in [c.value for c in PostCategory]:
        raise HTTPException(status_code=400, detail=f"Invalid category: {body.category}")
    
    # Validate status
    if body.status not in [s.value for s in PostStatus]:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
    
    post = await BulletinBoardManager.create_post(
        title=body.title,
        content=body.content,
        category=body.category,
        author_id=admin["id"],
        author_email=admin["email"],
        author_name=admin.get("name", admin["email"].split("@")[0]),
        priority=body.priority,
        target_audience=body.target_audience,
        status=body.status,
        featured_image=body.featured_image,
        attachments=body.attachments,
        tags=body.tags,
        scheduled_at=body.scheduled_at,
        expires_at=body.expires_at,
        pinned=body.pinned,
        allow_comments=body.allow_comments,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        og_image=body.og_image,
    )
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.post.create",
        resource_type="post",
        resource_id=post.post_id,
        ip_address=ip,
        user_agent=ua,
        after_state={"title": post.title, "status": post.status, "category": post.category},
    )
    
    return {"success": True, "post": post.to_dict()}


@router.get("/api/v1/admin/bulletin/posts/{post_id}")
async def admin_get_post(request: Request, post_id: str):
    """Get full post details (admin)."""
    auth = await require_admin(request, "content.read")
    
    post = await BulletinBoardManager.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {"post": post.to_dict()}


@router.put("/api/v1/admin/bulletin/posts/{post_id}")
async def admin_update_post(
    request: Request,
    post_id: str,
    body: UpdatePostRequest,
):
    """Update a post."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    
    # Build updates dict from non-None fields
    updates = {}
    for field_name, value in body.model_dump().items():
        if value is not None:
            updates[field_name] = value
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = await BulletinBoardManager.update_post(
        post_id=post_id,
        updates=updates,
        editor_id=admin["id"],
        editor_email=admin["email"],
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.post.update",
        resource_type="post",
        resource_id=post_id,
        ip_address=ip,
        user_agent=ua,
        after_state=updates,
    )
    
    return {"success": True, "post": updated.to_dict()}


@router.delete("/api/v1/admin/bulletin/posts/{post_id}")
async def admin_delete_post(request: Request, post_id: str):
    """Delete (archive) a post."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    
    result = await BulletinBoardManager.delete_post(post_id)
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.post.delete",
        resource_type="post",
        resource_id=post_id,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": True, "message": "Post archived"}


@router.post("/api/v1/admin/bulletin/posts/{post_id}/publish")
async def admin_publish_post(request: Request, post_id: str):
    """Publish a post immediately."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    
    updated = await BulletinBoardManager.update_post(
        post_id=post_id,
        updates={"status": "published"},
        editor_id=admin["id"],
        editor_email=admin["email"],
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.post.publish",
        resource_type="post",
        resource_id=post_id,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": True, "published_at": updated.published_at}


@router.post("/api/v1/admin/bulletin/posts/{post_id}/unpublish")
async def admin_unpublish_post(request: Request, post_id: str):
    """Unpublish a post (move to draft)."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    
    updated = await BulletinBoardManager.update_post(
        post_id=post_id,
        updates={"status": "draft"},
        editor_id=admin["id"],
        editor_email=admin["email"],
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.post.unpublish",
        resource_type="post",
        resource_id=post_id,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": True}


@router.post("/api/v1/admin/bulletin/posts/{post_id}/pin")
async def admin_pin_post(request: Request, post_id: str, body: dict = Body(...)):
    """Pin or unpin a post."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    
    pinned = body.get("pinned", True)
    pin_order = body.get("pin_order", 0)
    
    updated = await BulletinBoardManager.update_post(
        post_id=post_id,
        updates={"pinned": pinned, "pin_order": pin_order},
        editor_id=admin["id"],
        editor_email=admin["email"],
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Post not found")
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.post.pin" if pinned else "bulletin.post.unpin",
        resource_type="post",
        resource_id=post_id,
        ip_address=ip,
        user_agent=ua,
    )
    
    return {"success": True, "pinned": pinned}


@router.get("/api/v1/admin/bulletin/stats")
async def admin_bulletin_stats(request: Request):
    """Get bulletin board statistics."""
    auth = await require_admin(request, "content.read")
    
    stats = await BulletinBoardManager.get_stats()
    return {"stats": stats}


@router.get("/api/v1/admin/bulletin/scheduled")
async def admin_scheduled_posts(request: Request):
    """List scheduled posts waiting to be published."""
    auth = await require_admin(request, "content.read")
    
    result = await BulletinBoardManager.list_posts(
        status="scheduled",
        sort_by="scheduled_at",
        sort_order="asc",
    )
    return {"posts": result["posts"], "total": result["total"]}


@router.post("/api/v1/admin/bulletin/process-scheduled")
async def admin_process_scheduled(request: Request):
    """Process scheduled posts (publish ones that are due)."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    published = await BulletinBoardManager.publish_scheduled()
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.process_scheduled",
        resource_type="batch",
        resource_id="scheduled",
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"published_count": len(published)},
    )
    
    return {"success": True, "published": published, "count": len(published)}


@router.post("/api/v1/admin/bulletin/process-expired")
async def admin_process_expired(request: Request):
    """Process expired posts (archive ones past expiry)."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    archived = await BulletinBoardManager.archive_expired()
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action="bulletin.process_expired",
        resource_type="batch",
        resource_id="expired",
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        after_state={"archived_count": len(archived)},
    )
    
    return {"success": True, "archived": archived, "count": len(archived)}


# ── Comments (Admin Moderation) ─────────────────────────────

@router.get("/api/v1/admin/bulletin/posts/{post_id}/comments")
async def admin_get_comments(request: Request, post_id: str):
    """Get all comments for a post (admin moderation view)."""
    auth = await require_admin(request, "content.read")
    
    comments = await BulletinBoardManager.get_comments(post_id)
    return {"comments": comments, "total": len(comments)}


@router.post("/api/v1/admin/bulletin/comments/{comment_id}/moderate")
async def admin_moderate_comment(
    request: Request,
    comment_id: str,
    body: dict = Body(...),
):
    """Moderate a comment (approve/reject)."""
    auth = await require_admin(request, "content.write")
    admin = auth["admin"]
    
    status = body.get("status", "approved")
    
    # TODO: Implement comment moderation in bulletin_board.py
    
    await AuditLogger.log(
        admin_id=admin["id"],
        admin_email=admin["email"],
        action=f"bulletin.comment.{status}",
        resource_type="comment",
        resource_id=comment_id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    
    return {"success": True, "status": status}
