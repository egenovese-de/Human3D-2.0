"""Thread-safe in-memory job coordinator. Workers propose; coordinator promotes."""
from dataclasses import dataclass, replace
from threading import RLock
from uuid import uuid4


@dataclass(frozen=True)
class Job:
    id: str
    project_id: str
    generation: int
    dependencies: tuple[tuple[str, str], ...]
    kind: str
    state: str = "queued"
    completed: int = 0
    total: int = 0
    error: str = ""


class Coordinator:
    def __init__(self, project_id, *, history_limit=128):
        if type(history_limit) is not int or history_limit < 1:
            raise ValueError("invalid history limit")
        self.history_limit = history_limit
        self.project_id = project_id
        self.generation = 0
        self.dependencies = ()
        self._jobs = {}
        self._active = {}
        self._lock = RLock()

    def _prune(self):
        terminal = [key for key, job in self._jobs.items()
                    if job.state in {"succeeded", "failed", "cancelled", "stale"}]
        for key in terminal[:-self.history_limit]:
            del self._jobs[key]

    def snapshot(self):
        with self._lock:
            return tuple(self._jobs.values()), dict(self._active)

    def snapshot_with_generation(self):
        with self._lock:
            jobs, artifacts = self.snapshot()
            return self.generation, jobs, artifacts

    def invalidate(self, dependencies, *, retain_kind=None):
        with self._lock:
            dependencies = tuple(sorted(dependencies.items()))
            if dependencies != self.dependencies:
                self.dependencies = dependencies
                self.generation += 1
                if retain_kind in self._active:
                    revision, artifact = self._active[retain_kind]
                    if revision == self.generation - 1:
                        self._active[retain_kind] = (self.generation, artifact)
                for job in tuple(self._jobs.values()):
                    if job.state in {"queued", "running"}:
                        self._jobs[job.id] = replace(job, state="stale")
                self._prune()

    def submit(self, kind):
        with self._lock:
            for previous in tuple(self._jobs.values()):
                if previous.kind == kind and previous.state in {"queued", "running"}:
                    self._jobs[previous.id] = replace(previous, state="stale")
            self._prune()
            job = Job(str(uuid4()), self.project_id, self.generation,
                      self.dependencies, kind)
            self._jobs[job.id] = job
            return job

    def start(self, job_id):
        with self._lock:
            job = self._jobs[job_id]
            if job.state != "queued":
                raise ValueError("job not queued")
            self._jobs[job_id] = replace(job, state="running")

    def progress(self, job_id, completed, total):
        with self._lock:
            job = self._jobs[job_id]
            if job.state != "running" or not 0 <= job.completed <= completed <= total:
                raise ValueError("invalid progress")
            if job.total and job.total != total:
                raise ValueError("progress total changed")
            self._jobs[job_id] = replace(job, completed=completed, total=total)

    def cancel(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.state in {"queued", "running"}:
                self._jobs[job_id] = replace(job, state="cancelled" if job.state == "queued" else "cancelling")

    def cancellation_requested(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return job is None or job.state in {"cancelling", "cancelled", "stale"}

    def finish(self, job_id, artifact, validate, *, publish=None):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.state == "cancelling":
                self._jobs[job_id] = replace(job, state="cancelled")
                return False
            if job.state != "running":
                return False
            if job.generation != self.generation or job.dependencies != self.dependencies:
                self._jobs[job_id] = replace(job, state="stale")
                return False
        try:
            valid = bool(validate(artifact))
        except Exception:
            valid = False
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.state == "cancelling":
                self._jobs[job_id] = replace(job, state="cancelled")
                return False
            if job.state != "running" or job.generation != self.generation:
                return False
            if not valid:
                self._jobs[job_id] = replace(job, state="failed", error="validation_failed")
                return False
            if publish is not None:
                try:
                    publish()
                except Exception:
                    self._jobs[job_id] = replace(job, state="failed", error="publication_failed")
                    raise
            self._active[job.kind] = (job.generation, artifact)
            self._jobs[job_id] = replace(job, state="succeeded")
            self._prune()
            return True

    def fail(self, job_id, code):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.state in {"running", "cancelling"}:
                self._jobs[job_id] = replace(job, state="cancelled" if job.state == "cancelling" else "failed", error=code)

    def retry(self, job_id):
        with self._lock:
            job = self._jobs[job_id]
            if job.state not in {"failed", "cancelled", "stale"}:
                raise ValueError("job cannot be retried")
            return self.submit(job.kind)
