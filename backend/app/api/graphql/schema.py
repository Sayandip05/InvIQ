"""
Strawberry GraphQL schema + FastAPI router for the analytics layer.

Mounts at /graphql/analytics (registered in main.py).

GraphiQL playground is enabled only in development to avoid exposing
the interactive query editor in production — consistent with the pattern
used for FastAPI's own /docs endpoint elsewhere in the project.
"""

from __future__ import annotations
import strawberry
from strawberry.fastapi import GraphQLRouter

from app.api.graphql.resolvers import Query
from app.api.graphql.context import get_graphql_context
from app.core.config import settings

# Build the schema — Query only (all mutations stay in REST)
schema = strawberry.Schema(
    query=Query,
    # Scalar JSON is used for the heatmap matrix field.
    # Strawberry's built-in JSON scalar handles arbitrary dicts/lists.
    scalar_overrides={},
)

# GraphiQL playground is exposed in development only.
_graphql_ide = "graphiql" if settings.ENVIRONMENT != "production" else None

graphql_router = GraphQLRouter(
    schema,
    graphql_ide=_graphql_ide,
    context_getter=get_graphql_context,
)
