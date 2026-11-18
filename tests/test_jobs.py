from concurrent.futures import Executor, Future

from fastapi.testclient import TestClient

from libarrei import api
from libarrei.jobs import KEEP_SECONDS, JobStore


class Inline(Executor):
    """Runs work at submit time so tests need no waiting."""

    def submit(self, fn, *args):
        future = Future()
        future.set_result(fn(*args))
        return future


class Never(Executor):
    def submit(self, fn, *args):
        return Future()


def test_job_runs_and_reports_result():
    store = JobStore(lambda **q: {"echo": q}, Inline())
    job = store.submit({"isbn": "1"})
    assert (job.status, job.result) == ("done", {"echo": {"isbn": "1"}})


def test_failed_job_keeps_its_error():
    def boom(**_):
        raise RuntimeError("source down")

    job = JobStore(boom, Inline()).submit({"isbn": "1"})
    assert (job.status, job.error) == ("failed", "source down")


def test_same_unfinished_query_reuses_the_job():
    store = JobStore(lambda **q: q, Never())
    assert store.submit({"isbn": "1"}).id == store.submit({"isbn": "1"}).id


def test_finished_jobs_expire():
    now = [0.0]
    store = JobStore(lambda **q: q, Inline(), clock=lambda: now[0])
    job = store.submit({"isbn": "1"})
    now[0] = KEEP_SECONDS + 1
    assert store.get(job.id) is None


def test_job_endpoints(monkeypatch):
    monkeypatch.setattr(api, "jobs", JobStore(lambda **q: {"work": "merged"}, Inline()))
    client = TestClient(api.app)

    started = client.post("/v1/jobs", json={"title": "the hobbit"})
    assert started.status_code == 202
    polled = client.get(f"/v1/jobs/{started.json()['id']}").json()
    assert polled["status"] == "done" and polled["result"] == {"work": "merged"}
    assert client.get("/v1/jobs/nope").status_code == 404
    assert client.post("/v1/jobs", json={}).status_code == 422


def test_job_secrets_reach_the_run_but_are_never_shown():
    seen = {}
    store = JobStore(lambda **kw: seen.update(kw) or {}, Inline())
    job = store.submit({"isbn": "1"}, {"token": "abc"})
    assert seen["token"] == "abc"
    assert job.secrets == {} and "abc" not in repr(job) and job.query == {"isbn": "1"}
