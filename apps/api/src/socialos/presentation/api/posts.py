from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from socialos.application.common.auth import Actor
from socialos.application.posts.use_cases import CreatePost, CreatePostCommand, ListPosts
from socialos.infrastructure.database.session import SqlAlchemyUnitOfWork
from socialos.presentation.api.dependencies import get_actor
from socialos.presentation.api.schemas import CreatePostRequest, PostListResponse, PostResponse

router = APIRouter(prefix="/posts", tags=["posts"])


def get_create_post() -> CreatePost:
    return CreatePost(SqlAlchemyUnitOfWork)


def get_list_posts() -> ListPosts:
    return ListPosts(SqlAlchemyUnitOfWork)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    request: CreatePostRequest,
    actor: Annotated[Actor, Depends(get_actor)],
    use_case: Annotated[CreatePost, Depends(get_create_post)],
) -> PostResponse:
    post = await use_case.execute(
        actor,
        CreatePostCommand(content=request.content, scheduled_at=request.scheduled_at),
    )
    return PostResponse.from_domain(post)


@router.get("", response_model=PostListResponse)
async def list_posts(
    actor: Annotated[Actor, Depends(get_actor)],
    use_case: Annotated[ListPosts, Depends(get_list_posts)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PostListResponse:
    posts = await use_case.execute(actor, limit=limit, offset=offset)
    return PostListResponse(
        items=[PostResponse.from_domain(post) for post in posts],
        limit=limit,
        offset=offset,
    )
