"""Background jobs for slow full-edition fetches.

A cold fetch of every edition can take minutes, longer than an HTTP request
should stay open, so the API starts a job and the caller polls for it. Jobs
live in memory: a restart loses them, but the response cache keeps the work
already fetched, so resubmitting is cheap.
"""

import threading
import time
import uuid
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass, field

# Finished jobs are kept this long so a slow poller still gets its result.
KEEP_SECONDS = 3600
# Full fetches are rate-limited per source anyway; more workers would only queue on the limiters.
WORKERS = 2


@dataclass
class Job:
    id: str
    query: dict
    # Passed to the run but never shown or compared, e.g. a caller's token.
    secrets: dict = field(default_factory=dict, repr=False)
    status: str = "queued"  # queued, running, done or failed
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None


class JobStore:
    def __init__(self, run, executor: Executor | None = None, clock=time.time):
        self.run = run
        self.executor = executor or ThreadPoolExecutor(max_workers=WORKERS)
        self.clock = clock
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def submit(self, query: dict, secrets: dict | None = None) -> Job:
        """Starts a job, or returns the unfinished one already running this query."""
        with self.lock:
            self._prune()
            for job in self.jobs.values():
                if job.query == query and job.status in ("queued", "running"):
                    return job
            job = Job(id=uuid.uuid4().hex, query=query, secrets=secrets or {})
            self.jobs[job.id] = job
        self.executor.submit(self._work, job)
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            self._prune()
            return self.jobs.get(job_id)

    def _work(self, job: Job) -> None:
        job.status = "running"
        try:
            job.result = self.run(**job.query, **job.secrets)
            job.secrets = {}
            job.status = "done"
        except Exception as error:  # a failed job must report, not vanish
            job.error = str(error)
            job.status = "failed"
        job.finished_at = self.clock()

    def _prune(self) -> None:
        now = self.clock()
        for job_id in [j.id for j in self.jobs.values() if j.finished_at is not None and now - j.finished_at > KEEP_SECONDS]:
            del self.jobs[job_id]
