import tempfile
import unittest
from pathlib import Path

from scripts.models import WorkflowStep
from scripts.review_gate import ReviewDecision, ReviewGate, ReviewGateError


class InputScript:
    def __init__(self, responses):
        self.responses = list(responses)

    def __call__(self, prompt):
        if not self.responses:
            raise AssertionError("No scripted input remaining")
        return self.responses.pop(0)


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.output_path = self.root / "output.md"
        self.output_path.write_text("# Output\n\nContent", encoding="utf-8")
        self.step = WorkflowStep(
            step_number=0,
            step_id="00-test",
            name="Test",
            prompt_template_path="prompt.md",
            output_path="output.md",
        )

    def test_approve_decision(self):
        gate = ReviewGate(input_func=InputScript(["a"]))

        decision = gate.review(self.step, self.output_path)

        self.assertEqual(decision, ReviewDecision.APPROVE)

    def test_edit_decision_revalidates(self):
        gate = ReviewGate(input_func=InputScript(["e", ""]))

        decision = gate.review(self.step, self.output_path)

        self.assertEqual(decision, ReviewDecision.EDIT)

    def test_regenerate_decision(self):
        gate = ReviewGate(input_func=InputScript(["r"]))

        decision = gate.review(self.step, self.output_path)

        self.assertEqual(decision, ReviewDecision.REGENERATE)

    def test_skip_validation(self):
        gate = ReviewGate(input_func=InputScript(["s"]))

        decision = gate.review(self.step, self.output_path)

        self.assertEqual(decision, ReviewDecision.SKIP)

    def test_unsafe_skip_is_blocked(self):
        self.output_path.write_text("not markdown", encoding="utf-8")
        gate = ReviewGate(input_func=InputScript(["s"]))

        with self.assertRaises(ReviewGateError):
            gate.review(self.step, self.output_path)

    def test_quit_decision(self):
        gate = ReviewGate(input_func=InputScript(["q"]))

        decision = gate.review(self.step, self.output_path)

        self.assertEqual(decision, ReviewDecision.QUIT)

    def test_invalid_command_reprompts(self):
        gate = ReviewGate(input_func=InputScript(["x", "a"]))

        decision = gate.review(self.step, self.output_path)

        self.assertEqual(decision, ReviewDecision.APPROVE)


if __name__ == "__main__":
    unittest.main()
