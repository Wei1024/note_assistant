"""
Tag Management API Routes

Provides endpoints for:
- Tag search/autocomplete
- Tag CRUD operations
- Tag hierarchy navigation
- Tag statistics
"""
from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel
from ..repositories.tag_repository import TagRepository

router = APIRouter(prefix="/tags", tags=["tags"])


# ============================================================================
# Response Models
# ============================================================================

class TagResponse(BaseModel):
    """Tag information"""
    id: str
    name: str
    level: int
    use_count: int
    last_used_at: Optional[str] = None


class TagSearchResponse(BaseModel):
    """Tag search results"""
    tags: List[TagResponse]
    total: int


class TagWithChildrenResponse(BaseModel):
    """Tag with its children (for hierarchy navigation)"""
    id: str
    name: str
    level: int
    use_count: int
    children: List[TagResponse]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/search", response_model=TagSearchResponse)
async def search_tags(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results")
):
    """
    Search tags by name (fuzzy matching for autocomplete).

    **Matching strategy**:
    1. Exact match (highest priority)
    2. Prefix match (e.g., "proj" matches "project")
    3. Contains match (e.g., "api" matches "tech/api")
    4. Sorted by use_count (most used first)

    **Use case**: Autocomplete dropdown when user types `#proj`

    **Example**:
    ```
    GET /tags/search?q=proj&limit=10
    ```

    **Response**:
    ```json
    {
      "tags": [
        {"id": "uuid", "name": "project", "level": 0, "use_count": 23},
        {"id": "uuid", "name": "project/graphrag", "level": 1, "use_count": 4},
        {"id": "uuid", "name": "side-project", "level": 0, "use_count": 2}
      ],
      "total": 3
    }
    ```
    """
    results = TagRepository.search_tags(q, limit)

    tags = [
        TagResponse(
            id=tag['id'],
            name=tag['name'],
            level=tag['level'],
            use_count=tag['use_count'],
            last_used_at=tag.get('last_used_at')
        )
        for tag in results
    ]

    return TagSearchResponse(tags=tags, total=len(tags))


@router.get("/{tag_id}/children", response_model=TagWithChildrenResponse)
async def get_tag_children(tag_id: str):
    """
    Get a tag and its children (for hierarchical navigation).

    **Use case**: When user types `#project/`, show all project/* tags

    **Example**:
    ```
    GET /tags/{project_uuid}/children
    ```

    **Response**:
    ```json
    {
      "id": "uuid",
      "name": "project",
      "level": 0,
      "use_count": 23,
      "children": [
        {"id": "uuid", "name": "project/graphrag", "level": 1, "use_count": 4},
        {"id": "uuid", "name": "project/alpha", "level": 1, "use_count": 12}
      ]
    }
    ```
    """
    # Get parent tag info
    all_tags = TagRepository.get_all_tags()
    parent_tag = next((t for t in all_tags if t['id'] == tag_id), None)

    if not parent_tag:
        return TagWithChildrenResponse(
            id=tag_id,
            name="",
            level=0,
            use_count=0,
            children=[]
        )

    # Get children
    children = TagRepository.get_tag_children(parent_tag['name'])

    return TagWithChildrenResponse(
        id=parent_tag['id'],
        name=parent_tag['name'],
        level=parent_tag['level'],
        use_count=parent_tag['use_count'],
        children=[
            TagResponse(
                id=child['id'],
                name=child['name'],
                level=child['level'],
                use_count=child['use_count']
            )
            for child in children
        ]
    )


@router.get("", response_model=TagSearchResponse)
async def get_all_tags(
    include_unused: bool = Query(True, description="Include tags with use_count=0")
):
    """
    Get all tags (for tag management UI).

    **Example**:
    ```
    GET /tags?include_unused=false
    ```

    **Response**:
    ```json
    {
      "tags": [
        {"id": "uuid", "name": "project/graphrag", "level": 1, "use_count": 4},
        {"id": "uuid", "name": "client/acme", "level": 1, "use_count": 2},
        ...
      ],
      "total": 27
    }
    ```
    """
    results = TagRepository.get_all_tags(include_unused=include_unused)

    tags = [
        TagResponse(
            id=tag['id'],
            name=tag['name'],
            level=tag['level'],
            use_count=tag['use_count'],
            last_used_at=tag.get('last_used_at')
        )
        for tag in results
    ]

    return TagSearchResponse(tags=tags, total=len(tags))
