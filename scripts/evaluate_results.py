"""Run live retrieval and answer cross-checks against the onboarding golden set."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.embeddings import get_embedder  # noqa: E402
from backend.core.llm import get_llm  # noqa: E402
from backend.evaluation.crosscheck import (  # noqa: E402
    evaluate_retrieval,
    judge_answer_with_llm,
    semantic_answer_check,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate live RAG retrieval with Hit@K/MRR and optionally cross-check "
            "generated answers using embeddings and an LLM judge."
        )
    )
    parser.add_argument("--backend-url", default="http://localhost:7799")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evals" / "onboarding_retrieval.json",
    )
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--answers", action="store_true")
    parser.add_argument("--llm-judge", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-hit-rate", type=float, default=0.85)
    parser.add_argument("--min-mrr", type=float, default=0.70)
    parser.add_argument("--min-question-evidence", type=float, default=0.30)
    parser.add_argument("--min-claim-evidence", type=float, default=0.45)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation dataset must be a non-empty JSON array.")
    executed = []
    answer_results = []
    use_answers = args.answers or args.llm_judge
    embedder = get_embedder() if use_answers else None
    llm = get_llm() if args.llm_judge else None

    with httpx.Client(base_url=args.backend_url, timeout=120) as client:
        for case in cases:
            search = client.post(
                "/search",
                json={"query": case["question"], "top_k": args.top_k},
            )
            search.raise_for_status()
            hits = search.json().get("hits", [])
            executed.append({**case, "hits": hits})
            if not use_answers:
                continue
            generated = client.post(
                "/ask",
                json={
                    "question": case["question"],
                    "use_rag": True,
                    "top_k": args.top_k,
                    "agent": "motrun-onboarding",
                    "response_format": "plain",
                },
            )
            generated.raise_for_status()
            response = generated.json()
            passages = [
                str(hit.get("text", ""))
                for hit in response.get("retrieved", [])
            ]
            semantic = semantic_answer_check(
                case["question"],
                response.get("answer", ""),
                passages,
                embedder=embedder,
                min_question_evidence=args.min_question_evidence,
                min_claim_evidence=args.min_claim_evidence,
            )
            item = {
                "id": case["id"],
                "answer": response.get("answer"),
                "semantic": semantic,
            }
            if llm is not None:
                item["llm_judge"] = judge_answer_with_llm(
                    case["question"],
                    response.get("answer", ""),
                    passages,
                    llm=llm,
                )
            answer_results.append(item)

    retrieval = evaluate_retrieval(executed)
    report = {
        "dataset": str(args.dataset),
        "top_k": args.top_k,
        "retrieval": retrieval,
        "answers": answer_results,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")

    retrieval_passed = (
        retrieval["hit_at_k"] >= args.min_hit_rate
        and retrieval["mrr"] >= args.min_mrr
    )
    answers_passed = all(
        item["semantic"]["passed"]
        and (
            not args.llm_judge
            or item["llm_judge"].get("passed") is True
        )
        for item in answer_results
    )
    return 0 if retrieval_passed and answers_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
