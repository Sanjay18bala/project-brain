from __future__ import annotations

import asyncio
import logging

from .api.routes import _default_project_id, run_staleness_sweep
from .config import STALENESS_SWEEP_INTERVAL_SECONDS
from .db import get_conn

logger = logging.getLogger(__name__)


async def staleness_sweep_loop() -> None:
    """Runs the staleness sweep on a timer, in-process, rather than a separate scheduled
    job/container — the simplest thing that works at MVP scale (see docs/roadmap-v2.md).
    A production deployment with real scheduling infra (e.g. Nebius Serverless Jobs, per
    TechStack.md §14) could replace this loop with an external trigger calling the same
    run_staleness_sweep function via POST /projects/{id}/sweep.
    """
    while True:
        try:
            project_id = _default_project_id()
            with get_conn() as conn:
                stale_ids = run_staleness_sweep(conn, project_id)
            if stale_ids:
                logger.info("staleness sweep marked %d node(s) UNKNOWN", len(stale_ids))
        except Exception:
            logger.exception("staleness sweep failed")
        await asyncio.sleep(STALENESS_SWEEP_INTERVAL_SECONDS)
