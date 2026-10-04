import json
import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.plan_choice import CHOICE_MAX_TOKENS, model_chooser, parse_choice


class ScriptedGateway:
    """A local model that gives one prepared answer, or is unavailable."""

    def __init__(self, answer, mode="local-model"):
        self.answer, self.mode, self.calls = answer, mode, []

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        self.calls.append({"message": message, "context": context, "systemPrompt": system_prompt,
                           "maxTokens": max_tokens})
        return self.answer, self.mode


PICKS = {"plans": [{"kind": "focused", "why": "Two work tasks fit one block.", "whyZh": "两项工作适合连续完成。"},
                   {"kind": "gentle", "why": "Energy was low.", "whyZh": "精力偏低。"}]}


class ParseChoiceTests(unittest.TestCase):
    def test_reads_the_plans_from_a_json_answer_even_inside_other_text(self):
        self.assertEqual(parse_choice(json.dumps(PICKS)), PICKS["plans"])
        self.assertEqual(parse_choice(f"Here you go:\n```json\n{json.dumps(PICKS, ensure_ascii=False)}\n```"),
                         PICKS["plans"])

    def test_an_answer_without_usable_json_gives_nothing(self):
        for answer in ("I would pick Deep focus.", "{not json}", json.dumps({"plans": "focused"}), json.dumps([1, 2])):
            self.assertIsNone(parse_choice(answer), answer)

    def test_entries_that_are_not_objects_are_skipped(self):
        self.assertEqual(parse_choice(json.dumps({"plans": ["focused", PICKS["plans"][0]]})), [PICKS["plans"][0]])


class ModelChooserTests(unittest.TestCase):
    def test_the_model_reads_the_day_as_json_and_answers_in_both_languages(self):
        gateway = ScriptedGateway(json.dumps(PICKS, ensure_ascii=False))
        context = {"day": {"tasks": [{"title": "法语"}]}, "candidates": [{"kind": "focused"}]}
        self.assertEqual(model_chooser(gateway)(context), PICKS["plans"])
        call = gateway.calls[0]
        self.assertEqual(json.loads(call["context"]), context)
        self.assertIn("Orchestrator", call["systemPrompt"])
        self.assertIn('"whyZh"', call["message"])
        self.assertEqual(call["maxTokens"], CHOICE_MAX_TOKENS)

    def test_without_the_model_there_is_no_choice(self):
        self.assertIsNone(model_chooser(ScriptedGateway("The model is not available.", "rules"))({"candidates": []}))


if __name__ == "__main__":
    unittest.main()
