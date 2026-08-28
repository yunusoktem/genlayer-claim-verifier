# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


class ClaimVerifier(gl.Contract):
    claim: str
    source_url: str
    verdict: str
    confidence: str
    evidence: str
    verification_status: str

    def __init__(self, claim: str, source_url: str):
        self.claim = claim
        self.source_url = source_url
        self.verdict = "PENDING"
        self.confidence = "PENDING"
        self.evidence = ""
        self.verification_status = "PENDING"

    @gl.public.write
    def verify_claim(self) -> None:
        claim = self.claim
        source_url = self.source_url

        # Leader independently retrieves the source and evaluates the claim.
        def leader_fn():
            response = gl.nondet.web.get(source_url)
            page_text = response.body.decode("utf-8")[:12000]

            prompt = f"""
You are the primary fact verifier in a decentralized verification system.

Your task is to determine whether the CLAIM is supported by the SOURCE CONTENT.

CLAIM:
{claim}

SOURCE CONTENT:
{page_text}

Rules:
- TRUE only when the source clearly supports the claim.
- FALSE only when the source clearly contradicts the claim.
- UNCERTAIN when the source does not provide enough reliable evidence.
- Do not use outside knowledge.
- Base the verdict only on the supplied source.
- Evidence must briefly explain the relevant information from the source.

Return ONLY JSON:

{{
  "verdict": "TRUE" or "FALSE" or "UNCERTAIN",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "evidence": "short evidence-based explanation"
}}
"""

            result = gl.nondet.exec_prompt(
                prompt,
                response_format="json"
            )

            if not isinstance(result, dict):
                raise gl.UserError("Primary verifier did not return a JSON object.")

            if result.get("verdict") not in (
                "TRUE",
                "FALSE",
                "UNCERTAIN"
            ):
                raise gl.UserError("Invalid primary verdict.")

            if result.get("confidence") not in (
                "HIGH",
                "MEDIUM",
                "LOW"
            ):
                raise gl.UserError("Invalid primary confidence.")

            if not isinstance(result.get("evidence"), str):
                raise gl.UserError("Primary evidence is not text.")

            if not result.get("evidence").strip():
                raise gl.UserError("Primary evidence is empty.")

            return result

        # Validator independently retrieves the source and performs
        # a second verification instead of trusting the leader's labels.
        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            leader_data = leader_result.calldata

            if not isinstance(leader_data, dict):
                return False

            leader_verdict = leader_data.get("verdict")

            if leader_verdict not in (
                "TRUE",
                "FALSE",
                "UNCERTAIN"
            ):
                return False

            if not isinstance(leader_data.get("evidence"), str):
                return False

            if not leader_data.get("evidence").strip():
                return False

            # Independent source retrieval by the validator.
            response = gl.nondet.web.get(source_url)
            page_text = response.body.decode("utf-8")[:12000]

            validator_prompt = f"""
You are an independent validator in a decentralized fact-verification
system.

Independently evaluate the claim below using ONLY the supplied source.

CLAIM:
{claim}

SOURCE CONTENT:
{page_text}

Important:
- Do not trust any previous verifier.
- Perform your own analysis of the source.
- TRUE means the source clearly supports the claim.
- FALSE means the source clearly contradicts the claim.
- UNCERTAIN means the source does not provide enough evidence.
- Do not use outside knowledge.

Return ONLY JSON:

{{
  "verdict": "TRUE" or "FALSE" or "UNCERTAIN",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "evidence": "short independent explanation based only on the source"
}}
"""

            validator_data = gl.nondet.exec_prompt(
                validator_prompt,
                response_format="json"
            )

            if not isinstance(validator_data, dict):
                return False

            validator_verdict = validator_data.get("verdict")

            if validator_verdict not in (
                "TRUE",
                "FALSE",
                "UNCERTAIN"
            ):
                return False

            if validator_data.get("confidence") not in (
                "HIGH",
                "MEDIUM",
                "LOW"
            ):
                return False

            if not isinstance(validator_data.get("evidence"), str):
                return False

            if not validator_data.get("evidence").strip():
                return False

            # The critical consensus gate:
            # an independently derived verdict must agree with the leader.
            return validator_verdict == leader_verdict

        result = gl.vm.run_nondet_unsafe(
            leader_fn,
            validator_fn
        )

        self.verdict = result["verdict"]
        self.confidence = result["confidence"]
        self.evidence = result["evidence"]
        self.verification_status = "CONSENSUS_VERIFIED"

    @gl.public.view
    def get_result(self) -> dict:
        return {
            "claim": self.claim,
            "source_url": self.source_url,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "verification_status": self.verification_status,
        }
