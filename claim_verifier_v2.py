# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json


class ClaimVerifierV3(gl.Contract):

    claim: str

    source_url_1: str
    source_url_2: str
    source_url_3: str

    verdict: str
    confidence: str
    evidence: str
    validator_verdict: str

    source_1_verdict: str
    source_2_verdict: str
    source_3_verdict: str

    source_1_evidence: str
    source_2_evidence: str
    source_3_evidence: str

    agreement_count: int

    def __init__(
        self,
        claim: str,
        source_url_1: str,
        source_url_2: str,
        source_url_3: str
    ):
        self.claim = claim

        self.source_url_1 = source_url_1
        self.source_url_2 = source_url_2
        self.source_url_3 = source_url_3

        self.verdict = "PENDING"
        self.confidence = "PENDING"
        self.evidence = ""
        self.validator_verdict = "PENDING"

        self.source_1_verdict = "PENDING"
        self.source_2_verdict = "PENDING"
        self.source_3_verdict = "PENDING"

        self.source_1_evidence = ""
        self.source_2_evidence = ""
        self.source_3_evidence = ""

        self.agreement_count = 0

    def _evaluate_sources(self):

        urls = [
            self.source_url_1,
            self.source_url_2,
            self.source_url_3
        ]

        source_texts = []

        for url in urls:
            response = gl.nondet.web.get(url)

            try:
                text = response.body.decode("utf-8")
            except Exception:
                text = ""

            # Limit the amount of external content passed to the model.
            text = text[:10000]

            source_texts.append(text)

        prompt = f"""
You are an independent fact verification system.

Your task is to evaluate the CLAIM against THREE independent web sources.

CLAIM:
{self.claim}

SOURCE 1:
{source_texts[0]}

SOURCE 2:
{source_texts[1]}

SOURCE 3:
{source_texts[2]}

IMPORTANT RULES:

1. Evaluate each source independently.
2. Use ONLY information contained in that source.
3. Ignore HTML scripts, JavaScript, CSS, navigation,
   tracking data, metadata, and unrelated page elements.
4. If the useful factual content of a source is unavailable,
   return UNCERTAIN for that source.
5. TRUE means the source clearly supports the claim.
6. FALSE means the source clearly contradicts the claim.
7. UNCERTAIN means the source does not contain enough
   usable evidence.
8. Do not use outside knowledge.
9. Keep evidence brief and factual.

After evaluating all three sources, calculate the overall verdict:

- If at least two sources are TRUE, overall verdict = TRUE.
- If at least two sources are FALSE, overall verdict = FALSE.
- Otherwise overall verdict = UNCERTAIN.

Confidence:

- HIGH if all three source verdicts agree.
- MEDIUM if two sources agree and one differs.
- LOW if there is no clear majority.

Return JSON with EXACTLY these fields:

{{
  "source_1_verdict": "TRUE" | "FALSE" | "UNCERTAIN",
  "source_1_evidence": "brief evidence",

  "source_2_verdict": "TRUE" | "FALSE" | "UNCERTAIN",
  "source_2_evidence": "brief evidence",

  "source_3_verdict": "TRUE" | "FALSE" | "UNCERTAIN",
  "source_3_evidence": "brief evidence",

  "verdict": "TRUE" | "FALSE" | "UNCERTAIN",
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}}
"""

        result = gl.nondet.exec_prompt(
            prompt,
            response_format="json"
        )

        if not isinstance(result, dict):
            raise gl.UserError("Invalid verifier response")

        valid_verdicts = (
            "TRUE",
            "FALSE",
            "UNCERTAIN"
        )

        valid_confidence = (
            "HIGH",
            "MEDIUM",
            "LOW"
        )

        for i in range(1, 4):
            verdict = result.get(f"source_{i}_verdict")
            evidence = result.get(f"source_{i}_evidence")

            if verdict not in valid_verdicts:
                raise gl.UserError(
                    f"Invalid source {i} verdict"
                )

            if not isinstance(evidence, str):
                raise gl.UserError(
                    f"Invalid source {i} evidence"
                )

        overall_verdict = result.get("verdict")
        confidence = result.get("confidence")

        if overall_verdict not in valid_verdicts:
            raise gl.UserError("Invalid overall verdict")

        if confidence not in valid_confidence:
            raise gl.UserError("Invalid confidence")

        return result

    def _calculate_majority(self, results):

        verdicts = [
            results["source_1_verdict"],
            results["source_2_verdict"],
            results["source_3_verdict"]
        ]

        true_count = verdicts.count("TRUE")
        false_count = verdicts.count("FALSE")

        if true_count >= 2:
            return "TRUE", true_count

        if false_count >= 2:
            return "FALSE", false_count

        return "UNCERTAIN", 1

    @gl.public.write
    def verify_claim(self) -> None:

        def leader_fn():
            result = self._evaluate_sources()

            majority_verdict, agreement = (
                self._calculate_majority(result)
            )

            # The deterministic majority rule is the final decision.
            result["verdict"] = majority_verdict
            result["agreement_count"] = agreement

            return result

        def validator_fn(leader_result) -> bool:

            if not isinstance(
                leader_result,
                gl.vm.Return
            ):
                return False

            leader_data = leader_result.calldata

            if not isinstance(
                leader_data,
                dict
            ):
                return False

            validator_data = self._evaluate_sources()

            validator_verdict, validator_agreement = (
                self._calculate_majority(
                    validator_data
                )
            )

            leader_verdict, leader_agreement = (
                self._calculate_majority(
                    leader_data
                )
            )

            # The validator independently reproduces
            # the three source decisions and majority result.
            return (
                validator_verdict == leader_verdict
                and validator_agreement == leader_agreement
                and validator_data["source_1_verdict"]
                == leader_data["source_1_verdict"]
                and validator_data["source_2_verdict"]
                == leader_data["source_2_verdict"]
                and validator_data["source_3_verdict"]
                == leader_data["source_3_verdict"]
            )

        result = gl.vm.run_nondet_unsafe(
            leader_fn,
            validator_fn
        )

        self.verdict = result["verdict"]
        self.confidence = result["confidence"]

        self.source_1_verdict = (
            result["source_1_verdict"]
        )
        self.source_2_verdict = (
            result["source_2_verdict"]
        )
        self.source_3_verdict = (
            result["source_3_verdict"]
        )

        self.source_1_evidence = (
            result["source_1_evidence"]
        )
        self.source_2_evidence = (
            result["source_2_evidence"]
        )
        self.source_3_evidence = (
            result["source_3_evidence"]
        )

        self.agreement_count = (
            result["agreement_count"]
        )

        self.evidence = (
            "Source 1: "
            + self.source_1_evidence
            + "\nSource 2: "
            + self.source_2_evidence
            + "\nSource 3: "
            + self.source_3_evidence
        )

        self.validator_verdict = self.verdict

    @gl.public.view
    def get_result(self) -> dict:
        return {
            "claim": self.claim,

            "source_url_1": self.source_url_1,
            "source_url_2": self.source_url_2,
            "source_url_3": self.source_url_3,

            "verdict": self.verdict,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "validator_verdict": self.validator_verdict,

            "source_1_verdict": self.source_1_verdict,
            "source_2_verdict": self.source_2_verdict,
            "source_3_verdict": self.source_3_verdict,

            "source_1_evidence": self.source_1_evidence,
            "source_2_evidence": self.source_2_evidence,
            "source_3_evidence": self.source_3_evidence,

            "agreement_count": self.agreement_count
        }
