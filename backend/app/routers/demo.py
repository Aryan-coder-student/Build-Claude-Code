"""Demo-run execution API used by the chat iframe: one step per request."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models as m
from .. import repo
from ..agent import demo
from ..db import get_session
from ..schemas import AdvanceRequest, AdvanceResponse

router = APIRouter(prefix="/api/demo", tags=["demo"])
SessionDep = Annotated[Session, Depends(get_session)]


def _run(session: Session, run_id: str) -> m.DemoRun:
    run = repo.get_run_any_tenant(session, run_id)
    if run is None:
        raise HTTPException(404, "demo run not found")
    return run


@router.post("/runs/{run_id}/advance", response_model=AdvanceResponse, response_model_exclude_none=True)
def advance(run_id: str, body: AdvanceRequest, session: SessionDep):
    response = demo.advance(session, _run(session, run_id), body.result)
    session.commit()
    return response


@router.post("/runs/{run_id}/stop", response_model=AdvanceResponse, response_model_exclude_none=True)
def stop(run_id: str, session: SessionDep):
    run = _run(session, run_id)
    demo.stop(session, run)
    response = demo.advance(session, run, None)
    session.commit()
    return response
