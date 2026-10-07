"""Pure success-only result selection for the GTK presentation layer."""

from __future__ import annotations

from collections.abc import Iterable

from .providers import ProviderOutcome


class PresentationState:
    """Track one generation of provider outcomes in configured priority order."""

    def __init__(self, provider_ids: Iterable[str], max_cards: int):
        self.provider_ids = tuple(dict.fromkeys(provider_ids))
        self.max_cards = max_cards
        self._priority = {provider_id: index for index, provider_id in enumerate(self.provider_ids)}
        self._outcomes: dict[str, ProviderOutcome] = {}

    def reset(self) -> None:
        self._outcomes.clear()

    def accept(self, outcome: ProviderOutcome) -> bool:
        """Record one known provider result, rejecting duplicates and stale ids."""
        provider_id = outcome.provider_id
        if provider_id not in self._priority or provider_id in self._outcomes:
            return False
        self._outcomes[provider_id] = outcome
        return True

    @property
    def visible_successes(self) -> tuple[ProviderOutcome, ...]:
        return tuple(
            outcome
            for provider_id in self.provider_ids
            if (outcome := self._outcomes.get(provider_id)) is not None and outcome.ok
        )[: self.max_cards]

    @property
    def complete(self) -> bool:
        return len(self._outcomes) == len(self.provider_ids)

    @property
    def loading(self) -> bool:
        return bool(self.provider_ids) and not self.complete

    @property
    def no_result(self) -> bool:
        return self.complete and not any(outcome.ok for outcome in self._outcomes.values())
