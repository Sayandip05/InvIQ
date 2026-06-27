"""
GraphQL context factory for Strawberry / FastAPI integration.

Builds a dict  {db: Session, user: Optional[User]}  that every resolver
receives via  info.context.  This mirrors the pattern used by the existing
REST dependency chain and lets GraphQL resolvers reuse the same auth /
session infrastructure without any duplication.
"""

from __future__ import annotations
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import get_db
from app.core.dependencies import get_optional_user
from app.infrastructure.database.models import User


async def get_graphql_context(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
) -> dict:
    """
    Strawberry context getter — injected into every query resolver via
    ``info.context``.

    Provides:
      - ``db``   : SQLAlchemy session (scoped to this request)
      - ``user`` : authenticated User model, or None for Guest / unauthenticated
    """
    return {"db": db, "user": user, "request": request}
