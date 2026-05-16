from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.team import Team, TeamMember, TeamRole
from app.models.user import User, UserRole
from app.schemas.team import (
    TeamCreate, TeamUpdate, TeamResponse,
    TeamMemberAdd, TeamMemberUpdate, TeamMemberResponse,
)
from app.dependencies import get_current_user, get_current_active_admin

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=list[TeamResponse], summary="获取团队列表")
async def list_teams(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_admin:
        result = await db.execute(select(Team).offset(skip).limit(limit))
    else:
        result = await db.execute(
            select(Team)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == current_user.id)
            .offset(skip).limit(limit)
        )
    return result.scalars().all()


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, summary="创建团队")
async def create_team(
    data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = Team(name=data.name, description=data.description)
    db.add(team)
    await db.flush()
    await db.refresh(team)

    # Creator becomes owner
    membership = TeamMember(
        team_id=team.id, user_id=current_user.id, role=TeamRole.owner
    )
    db.add(membership)
    return team


@router.get("/{team_id}", response_model=TeamResponse, summary="获取团队详情")
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if not current_user.is_admin:
        member_result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == current_user.id,
            )
        )
        if not member_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not a team member")
    return team


@router.put("/{team_id}", response_model=TeamResponse, summary="更新团队")
async def update_team(
    team_id: int,
    data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    await db.flush()
    await db.refresh(team)
    return team


@router.delete("/{team_id}", summary="删除团队")
async def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    await db.delete(team)
    return {"message": "Team deleted"}


# ===== Team Members =====
@router.get("/{team_id}/members", response_model=list[TeamMemberResponse], summary="获取团队成员")
async def list_members(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id)
    )
    return result.scalars().all()


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED, summary="添加团队成员")
async def add_member(
    team_id: int,
    data: TeamMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == data.user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    member = TeamMember(team_id=team_id, user_id=data.user_id, role=data.role)
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


@router.put("/{team_id}/members/{user_id}", response_model=TeamMemberResponse, summary="更新成员角色")
async def update_member(
    team_id: int,
    user_id: int,
    data: TeamMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = data.role
    await db.flush()
    await db.refresh(member)
    return member


@router.delete("/{team_id}/members/{user_id}", summary="移除团队成员")
async def remove_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == TeamRole.owner:
        raise HTTPException(status_code=400, detail="Cannot remove team owner")
    await db.delete(member)
    return {"message": "Member removed"}
