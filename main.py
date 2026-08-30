import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel
from typing_extensions import TypedDict

from pdf_loader import extract_text_from_pdf

load_dotenv()

MAX_CLAIM_TEXT_LENGTH = 10_000

model = ChatAnthropic(model="claude-sonnet-5", max_tokens=2048)


class ClaimData(BaseModel):
    claim_id: str
    policy_number: str
    claimant_name: str
    incident_date: date
    claim_amount: Decimal
    description: str
    claim_type: Literal["auto", "home"]

    claimant_contact: str | None = None
    adjuster_notes: str | None = None


class PolicyCheckResult(BaseModel):
    within_policy: bool
    violations: list[str]


class RiskAssessment(BaseModel):
    risk_score: int
    risk_flags: list[str]
    rationale: str


class ClaimState(TypedDict):
    raw_text: str
    claim_data: ClaimData | None
    validation_errors: list[str]
    policy_context: str
    policy_violations: list[str]
    risk_score: int
    risk_flags: list[str]
    decision: str | None
    human_decision: str | None
    notification: str | None
    extraction_error: str | None


def _load_policy_vector_store() -> InMemoryVectorStore:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    policy_dir = Path(__file__).parent / "policy_docs"
    texts = [p.read_text() for p in policy_dir.glob("*.md")]
    return InMemoryVectorStore.from_texts(texts, embeddings)


policy_store = _load_policy_vector_store()


def intake(state: ClaimState) -> dict:
    text = state["raw_text"].strip()
    if len(text) > MAX_CLAIM_TEXT_LENGTH:
        raise ValueError(
            f"Claim text is {len(text)} chars, exceeds the "
            f"{MAX_CLAIM_TEXT_LENGTH}-char limit; refusing to process."
        )
    return {"raw_text": text}


def extract(state: ClaimState) -> Command[Literal["validate", "notify"]]:
    extractor = model.with_structured_output(ClaimData)
    try:
        result = extractor.invoke(state["raw_text"])
    except Exception as exc:
        return Command(
            update={
                "claim_data": None,
                "extraction_error": str(exc),
                "decision": "extraction_failed",
            },
            goto="notify",
        )
    return Command(update={"claim_data": result}, goto="validate")


def validate(state: ClaimState) -> dict:
    claim = state["claim_data"]
    errors = []

    if claim.claim_amount <= 0:
        errors.append("claim_amount must be positive")
    if claim.incident_date > date.today():
        errors.append("incident_date is in the future")

    return {"validation_errors": errors}


def policy_check(state: ClaimState) -> dict:
    claim = state["claim_data"]
    query = f"{claim.claim_type} claim: {claim.description}, amount {claim.claim_amount}"
    matches = policy_store.similarity_search(query, k=3)
    context = "\n\n".join(m.page_content for m in matches)

    checker = model.with_structured_output(PolicyCheckResult)
    prompt = (
        f"Policy terms:\n{context}\n\n"
        f"Claim: type={claim.claim_type}, amount={claim.claim_amount}, "
        f"incident_date={claim.incident_date}, description={claim.description!r}\n\n"
        "Does this claim fall within the policy terms above? List any violations "
        "(e.g. exceeds payout limit, filed past deadline, matches an exclusion)."
    )
    result = checker.invoke(prompt)

    return {"policy_context": context, "policy_violations": result.violations}


def assess_risk(state: ClaimState) -> dict:
    claim = state["claim_data"]
    # Only send fields the risk model actually needs -- name/contact are PII
    # that add no signal to fraud scoring.
    claim_summary = {
        "claim_type": claim.claim_type,
        "claim_amount": str(claim.claim_amount),
        "incident_date": str(claim.incident_date),
        "description": claim.description,
    }
    assessor = model.with_structured_output(RiskAssessment)
    prompt = (
        f"Assess fraud/risk for this insurance claim on a 0-100 scale.\n"
        f"Claim: {claim_summary}\n"
        f"Validation issues: {state['validation_errors']}\n"
        f"Policy violations: {state['policy_violations']}\n"
        "Flag anything suspicious: vague descriptions, round-number amounts, "
        "mismatched dates, inconsistent details."
    )
    try:
        result = assessor.invoke(prompt)
    except Exception as exc:
        # Uncertainty guardrail: if the risk model's output can't be trusted,
        # fail toward human review, not toward a silent auto-approve or a crash.
        return {
            "risk_score": 100,
            "risk_flags": [f"risk assessment failed, defaulting to escalation: {exc}"],
        }
    return {"risk_score": result.risk_score, "risk_flags": result.risk_flags}


def decide(state: ClaimState) -> Command[Literal["human_review", "notify"]]:
    if state["validation_errors"]:
        decision = "auto_deny"
        goto = "notify"
    elif state["policy_violations"] or state["risk_score"] >= 50:
        decision = "escalate"
        goto = "human_review"
    else:
        decision = "auto_approve"
        goto = "notify"

    return Command(update={"decision": decision}, goto=goto)


def human_review(state: ClaimState) -> dict:
    response = interrupt(
        {
            "claim_id": state["claim_data"].claim_id,
            "risk_score": state["risk_score"],
            "risk_flags": state["risk_flags"],
            "question": "Approve or deny this escalated claim?",
        }
    )
    return {"human_decision": response, "decision": response}


def notify(state: ClaimState) -> dict:
    claim = state["claim_data"]
    if claim is None:
        message = (
            "Claim could not be processed automatically: "
            f"{state.get('extraction_error')}. Routed to manual intake."
        )
        return {"notification": message}

    outcome = state.get("human_decision") or state["decision"]
    message = (
        f"Dear {claim.claimant_name}, your claim {claim.claim_id} has been "
        f"{outcome}."
    )
    return {"notification": message}


builder = StateGraph(ClaimState)
builder.add_node("intake", intake)
builder.add_node("extract", extract)
builder.add_node("validate", validate)
builder.add_node("policy_check", policy_check)
builder.add_node("assess_risk", assess_risk)
builder.add_node("decide", decide)
builder.add_node("human_review", human_review)
builder.add_node("notify", notify)

builder.add_edge(START, "intake")
builder.add_edge("intake", "extract")
builder.add_edge("validate", "policy_check")
builder.add_edge("policy_check", "assess_risk")
builder.add_edge("assess_risk", "decide")
builder.add_edge("human_review", "notify")
builder.add_edge("notify", END)

graph = builder.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        raw_text = extract_text_from_pdf(pdf_path)
        thread_id = pdf_path.stem
        print(f"Loaded claim text from {pdf_path}")
    else:
        raw_text = """
        Claim ID: CLM-2026-00417
        Policy Number: POL-88213
        Claimant: Anita Rao
        Claim Type: auto
        Date of Incident: 2026-07-14
        Amount Claimed: $2,340.50
        Description: Rear windshield shattered by a fallen tree branch during a storm.
        Contact: anita.rao@example.com
        """
        thread_id = "demo-1"
        print("No PDF path given, using inline sample claim. "
              "Usage: python main.py sample_claims/<file>.pdf")

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "raw_text": raw_text,
        "claim_data": None,
        "validation_errors": [],
        "policy_context": "",
        "policy_violations": [],
        "risk_score": 0,
        "risk_flags": [],
        "decision": None,
        "human_decision": None,
        "notification": None,
        "extraction_error": None,
    }

    result = graph.invoke(initial_state, config=config)

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("ESCALATED FOR HUMAN REVIEW:", payload)
        human_answer = input("Enter decision (approved/denied): ")
        result = graph.invoke(Command(resume=human_answer), config=config)

    print(result["claim_data"])
    print("validation_errors:", result["validation_errors"])
    print("policy_violations:", result["policy_violations"])
    print("risk_score:", result["risk_score"], result["risk_flags"])
    print("decision:", result["decision"])
    print("notification:", result["notification"])
