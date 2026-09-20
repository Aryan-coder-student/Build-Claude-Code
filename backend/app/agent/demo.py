"""Sequential demo-run execution: hand out one typed action at a time and react to results."""

import json
import logging

from sqlalchemy.orm import Session

from .. import models as m
from .. import repo
from ..ids import new_id
from ..schemas import AdvanceResponse, DemoAction, StepResult

log = logging.getLogger(__name__)


def start_run(session: Session, tenant_id: str, product_id: str, session_id: str, title: str, steps: list[DemoAction]) -> m.DemoRun:
    # Only one active run per chat session.
    for run in repo.scoped(session, m.DemoRun, tenant_id, product_id):
        if run.session_id == session_id and run.status == "RUNNING":
            run.status = "STOPPED"
    run = m.DemoRun(
        id=new_id("run"), tenant_id=tenant_id, product_id=product_id, session_id=session_id, title=title,
        steps_json=json.dumps([s.model_dump(exclude_none=True) for s in steps]),
    )
    session.add(run)
    session.flush()
    log.info("demo run %s started: %s (%d steps)", run.id, title, len(steps))
    return run


def describe(action: DemoAction) -> str:
    target = action.label or action.selector or ""
    return {
        "navigate": f"Opening {action.label or action.path}…",
        "click": f"Clicking {target}…",
        "highlight": action.message or f"Highlighting {target}…",
        "scroll": f"Scrolling to {target}…",
        "type": f"Typing into {target}…",
        "wait": "One moment…",
        "explain": action.message or "",
    }[action.type]


def failure_message(action: DemoAction, error: str) -> str:
    target = action.label or action.selector or action.path or "that element"
    if "not found" in error.lower() or "timeout" in error.lower():
        return f"I couldn't find {target} on this screen. The page may have changed, so I've stopped the demo."
    return f"I ran into a problem while trying to {action.type} {target} ({error}). I've stopped the demo."


def advance(session: Session, run: m.DemoRun, result: StepResult | None) -> AdvanceResponse:
    steps = [DemoAction(**s) for s in json.loads(run.steps_json)]
    total = len(steps)

    def finished(message: str = "") -> AdvanceResponse:
        return AdvanceResponse(done=True, status=run.status, step_index=run.current_step, total_steps=total, message=message)

    if run.status != "RUNNING":
        return finished()
    if result is not None:
        if not result.ok:
            failed_action = steps[min(run.current_step, total - 1)]
            run.status, run.error = "FAILED", result.error
            message = failure_message(failed_action, result.error)
            repo.add_message(session, run.tenant_id, run.product_id, run.session_id, "assistant", message, {"demo_run_id": run.id, "event": "failed"})
            log.warning("demo run %s failed at step %d: %s", run.id, run.current_step, result.error)
            return finished(message)
        run.current_step += 1
    if run.current_step >= total:
        run.status = "DONE"
        log.info("demo run %s completed", run.id)
        return finished()
    action = steps[run.current_step]
    if action.type == "explain" and action.message:
        repo.add_message(session, run.tenant_id, run.product_id, run.session_id, "assistant", action.message, {"demo_run_id": run.id, "event": "explain"})
    return AdvanceResponse(done=False, status=run.status, step_index=run.current_step, total_steps=total, action=action, message=describe(action))


def stop(session: Session, run: m.DemoRun) -> None:
    if run.status == "RUNNING":
        run.status = "STOPPED"
        repo.add_message(session, run.tenant_id, run.product_id, run.session_id, "assistant", "Demo stopped. Ask me anything else whenever you're ready.", {"demo_run_id": run.id, "event": "stopped"})
