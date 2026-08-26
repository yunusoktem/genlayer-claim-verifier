# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


class ClaimVerifier(gl.Contract):
    claim: str
    source_url: str
    verdict: str
    confidence: str
    evidence: str

    def __init__(self, claim: str, source_url: str):
        self.claim = claim
        self.source_url = source_url
        self.verdict = "PENDING"
        self.confidence = "PENDING"
        self.evidence = ""

    @gl.public.write
    def verify_claim(self) -> None:
        claim = self.claim
        source_url = self.source_url

        def leader_fn():
            response = gl.nondet.web.get(source_url)
            page_text = response.body.decode("utf-8")[:12000]

            prompt = f"""
You are a decentralized fact verifier.

Evaluate the claim using the provided source.

CLAIM:
{claim}

SOURCE CONTENT:
{page_text}

Return ONLY valid JSON:
{{
  "verdict": "TRUE" or "FALSE" or "UNCERTAIN",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "evidence": "short explanation based only on the source"
}}
"""

            return gl.nondet.exec_prompt(
                prompt,
                response_format="json"
            )

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            proposed = leader_result.calldata

            if not isinstance(proposed, dict):
                return False

            if proposed.get("verdict") not in {
                "TRUE",
                "FALSE",
                "UNCERTAIN"
            }:
                return False

            if proposed.get("confidence") not in {
                "HIGH",
                "MEDIUM",
                "LOW"
            }:
                return False

            validator_result = leader_fn()

            if not isinstance(validator_result, dict):
                return False

            return (
                validator_result.get("verdict")
                == proposed.get("verdict")
            )

        result = gl.vm.run_nondet_unsafe(
            leader_fn,
            validator_fn
        )

        self.verdict = result["verdict"]
        self.confidence = result["confidence"]
        self.evidence = result["evidence"]

    @gl.public.view
    def get_result(self) -> dict:
        return {
            "claim": self.claim,
            "source_url": self.source_url,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }
