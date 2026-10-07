from __future__ import annotations

from tests.translate_support import ENTRY, setUpModule, tearDownModule  # noqa: F401

import unittest

from orbit_translate.presentation import PresentationState
from orbit_translate.providers import ProviderOutcome


def success(provider_id: str) -> ProviderOutcome:
    return ProviderOutcome(provider_id, provider_id, text=f"{provider_id} result")


def failure(provider_id: str) -> ProviderOutcome:
    return ProviderOutcome(
        provider_id,
        provider_id,
        error_category="network",
        error_message="unavailable",
    )


class PresentationStateTests(unittest.TestCase):
    def test_arrival_order_does_not_change_configured_priority(self) -> None:
        state = PresentationState(("first", "second", "third"), max_cards=3)

        self.assertTrue(state.accept(success("third")))
        self.assertTrue(state.accept(success("second")))
        self.assertTrue(state.accept(success("first")))

        self.assertEqual(
            [outcome.provider_id for outcome in state.visible_successes],
            ["first", "second", "third"],
        )

    def test_max_cards_limits_successes_after_failures(self) -> None:
        state = PresentationState(("failed", "preferred", "later"), max_cards=1)

        self.assertTrue(state.accept(failure("failed")))
        self.assertTrue(state.accept(success("later")))
        self.assertEqual([item.provider_id for item in state.visible_successes], ["later"])
        self.assertTrue(state.accept(success("preferred")))

        self.assertEqual([item.provider_id for item in state.visible_successes], ["preferred"])
        self.assertTrue(state.complete)

    def test_all_failed_providers_produce_only_terminal_no_result_state(self) -> None:
        state = PresentationState(("one", "two"), max_cards=2)

        self.assertTrue(state.loading)
        self.assertFalse(state.no_result)
        self.assertTrue(state.accept(failure("one")))
        self.assertTrue(state.loading)
        self.assertTrue(state.accept(failure("two")))

        self.assertTrue(state.complete)
        self.assertTrue(state.no_result)
        self.assertEqual(state.visible_successes, ())

    def test_duplicate_and_unknown_outcomes_are_discarded(self) -> None:
        state = PresentationState(("known", "pending"), max_cards=2)

        self.assertTrue(state.accept(success("known")))
        self.assertFalse(state.accept(failure("known")))
        self.assertFalse(state.accept(success("unknown")))
        self.assertFalse(state.complete)
        self.assertEqual([item.provider_id for item in state.visible_successes], ["known"])

    def test_reset_discards_outcomes_and_allows_fresh_generation_results(self) -> None:
        state = PresentationState(("one", "two"), max_cards=1)
        self.assertTrue(state.accept(success("one")))
        self.assertTrue(state.accept(failure("two")))
        self.assertTrue(state.complete)

        state.reset()

        self.assertFalse(state.complete)
        self.assertTrue(state.loading)
        self.assertEqual(state.visible_successes, ())
        self.assertTrue(state.accept(failure("one")))
        self.assertTrue(state.accept(success("two")))
        self.assertEqual([item.provider_id for item in state.visible_successes], ["two"])


if __name__ == "__main__":
    unittest.main()
