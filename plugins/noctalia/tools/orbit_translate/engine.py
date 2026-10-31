"""Bounded, daemon-threaded provider execution."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from queue import Empty, Queue
import threading

from .config import ProviderConfig
from .providers import ProviderOutcome, translate_provider


class ResultRelay:
    """Buffer worker outcomes until the UI attaches, then forward them.

    Lets requests start before GTK is imported and the window is built.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: list[ProviderOutcome] = []
        self._target: Callable[[ProviderOutcome], None] | None = None

    def __call__(self, outcome: ProviderOutcome) -> None:
        with self._lock:
            target = self._target
            if target is None:
                self._pending.append(outcome)
                return
        target(outcome)

    def attach(self, target: Callable[[ProviderOutcome], None]) -> None:
        with self._lock:
            pending, self._pending = self._pending, []
            self._target = target
        for outcome in pending:
            target(outcome)


@dataclass(frozen=True)
class ProviderJob:
    provider: ProviderConfig


class ProviderEngine:
    def __init__(
        self,
        providers: Iterable[ProviderConfig],
        text: str,
        source: str,
        target: str,
        timeout_ms: int,
        max_parallel: int,
        on_result: Callable[[ProviderOutcome], None],
    ):
        self._providers = tuple(providers)
        self._text = text
        self._source = source
        self._target = target
        self._timeout_ms = timeout_ms
        self._max_parallel = min(max_parallel, max(1, len(self._providers)))
        self._on_result = on_result
        self._queue: Queue[ProviderJob | None] = Queue()
        self._closed = threading.Event()
        self._workers: list[threading.Thread] = []

    def start(self) -> "ProviderEngine":
        for provider in self._providers:
            self._queue.put(ProviderJob(provider))
        for index in range(self._max_parallel):
            worker = threading.Thread(
                target=self._worker,
                name=f"orbit-translate-{index}",
                daemon=True,
            )
            self._workers.append(worker)
            worker.start()
        return self

    def close(self) -> None:
        self._closed.set()

    def _worker(self) -> None:
        while not self._closed.is_set():
            try:
                job = self._queue.get(timeout=0.1)
            except Empty:
                return
            try:
                if job is None:
                    return
                outcome = translate_provider(
                    job.provider,
                    self._text,
                    self._source,
                    self._target,
                    self._timeout_ms,
                )
                if not self._closed.is_set():
                    self._on_result(outcome)
            finally:
                self._queue.task_done()
