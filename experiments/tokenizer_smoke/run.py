"""Manual real-tokenizer building-block probes. Run on the MLX Mac."""
from copy import deepcopy
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

CASES = ("valid", "state", "instructions", "option", "shared_head")


def payload(case):
    text = "I cannot log in to my account."
    question = {
        "type": "choice", "instructions": "Which department should handle this?",
        "criteria": {"billing": "invoices and refunds",
                     "technical": "bugs and login issues", "sales": "pricing and upgrades"},
    }
    expected = set()
    if case == "state":
        text = "account login problem " * 3000
        expected = {"state", "full_request"}
    elif case == "instructions":
        question["instructions"] = "Choose the appropriate department carefully. " * 1000
        expected = {"instructions"}
    elif case == "option":
        question["criteria"]["technical"] = "technical login issue " * 1000
        expected = {"option_text"}
    elif case == "shared_head":
        question["criteria"] = {
            f"department_{i}": "account login billing refund issue " * 5 for i in range(24)
        }
        expected = {"shared_head_option"}
    elif case != "valid":
        raise ValueError(case)
    return text, question, expected


class ObservedRegistry:
    """Observe dispatch without replacing the real registry's tokenizer capability."""
    def __init__(self, registry):
        self.registry = registry
        self.calls = 0

    def get_inspector(self, config):
        return self.registry.get_inspector(config)

    def get_agent(self, config):
        agent = self.registry.get_agent(config)
        outer = self

        class ObservedAgent:
            def predict(self, *args, **kwargs):
                outer.calls += 1
                return agent.predict(*args, **kwargs)
        return ObservedAgent()


def main(default_case=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=(*CASES, "all"), default=default_case or "valid")
    parser.add_argument("--model-path", required=True,
                        help="Existing local typed-decisions MLX checkpoint directory; no download")
    args = parser.parse_args()
    model_path = Path(args.model_path).expanduser().resolve()
    if not model_path.is_dir():
        parser.error("--model-path must be an existing checkpoint directory")

    # These imports and model loading happen only on an explicit run, not --help.
    from laya_context_router.laya.config import RunConfig
    from laya_context_router.laya.registry import AgentRegistry
    from laya_context_router.laya.budget import InputBudgetError, InputTokenBudgetExceeded
    from laya_context_router.building_blocks.questions.ticket_triage_v2.block import run

    def loader(model, **kwargs):
        import laya_mlx
        return laya_mlx.load(str(model_path), local_files_only=True, **kwargs)

    config = RunConfig()
    registry = ObservedRegistry(AgentRegistry(loader=loader))
    outcomes = []
    for case in CASES if args.case == "all" else (args.case,):
        text, question, expected = payload(case)
        before = registry.calls
        try:
            result = run({"text": text}, config=config, registry=registry,
                         question_overrides={"department": deepcopy(question)}, strict=True)
            outcome = {"case": case, "passed": case == "valid" and registry.calls - before == 1,
                       "status": "predicted", "result": asdict(result)}
        except InputBudgetError as exc:
            boundaries = {v["boundary"] for v in exc.report.get("violations", [])}
            outcome = {"case": case,
                       "passed": bool(expected) and isinstance(exc, InputTokenBudgetExceeded)
                                 and expected <= boundaries and registry.calls == before,
                       "status": type(exc).__name__, "report": exc.report}
        except Exception as exc:
            outcome = {"case": case, "passed": False, "status": type(exc).__name__,
                       "message": str(exc)}
        outcome["prediction_calls"] = registry.calls - before
        outcomes.append(outcome)
        print(json.dumps(outcome, indent=2, ensure_ascii=False, default=str))
        print(("PASS" if outcome["passed"] else "FAIL") + ": " + case)
    return 0 if all(row["passed"] for row in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
