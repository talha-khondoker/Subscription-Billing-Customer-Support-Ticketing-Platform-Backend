# ----------------------------------------------------------------------
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import current_org_admin
from app.models.user import User
from app.schemas.user import AgentCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/agents", response_model=UserOut, status_code=201)
def create_agent(data: AgentCreate, db: Session = Depends(get_db), actor: User = Depends(current_org_admin)):
    try:
        result = user_service.create_agent(db, actor.organization_id, data)
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise


@router.get("/agents", response_model=list[UserOut])
def list_agents(db: Session = Depends(get_db), actor: User = Depends(current_org_admin)):
    return user_service.list_agents(db, actor.organization_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(current_org_admin)):
    try:
        result = user_service.update_user(db, actor.organization_id, user_id, data)
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise
# app/routers/users.py
# Owner:   Member 1
# Purpose: HTTP layer only: validate input, check role, call a service, return a schema. No business rules.
# ----------------------------------------------------------------------
# Notes:
#   Roles: SA Super Admin, OA Org Admin, AG Agent, CU Customer. Prefix: /api/v1
# TODO:
#   - POST  /users/agents [OA]  create agent
#   - GET   /users/agents [OA]  list agents
#   - PATCH /users/{id} [OA]  update or deactivate
