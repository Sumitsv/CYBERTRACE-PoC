import hashlib
from typing import List, Dict, Any

def calculate_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def generate_investigative_brief(
    file_name: str,
    record_count: int,
    sha256_hash: str,
    entities_count: int,
    relationships_count: int,
    risk_score: int,
    risk_level: str,
    signals: List[Dict[str, Any]],
    top_entities: List[str]
) -> str:
    signals_text = "\n".join(
        [f"  - [{s['weight']} pts] {s['name']}: {s['description']}" for s in signals]
    ) if signals else "  - No immediate heuristics triggered."

    brief = f"""================================================================================
CYBERTRACE - AUTOMATED DIGITAL ARTIFACT CORRELATION BRIEF
Synthetic Evidence Investigation Workspace
================================================================================

1. EVIDENCE PROVENANCE & INTEGRITY
--------------------------------------------------------------------------------
Source File     : {file_name}
Total Records   : {record_count}
SHA-256 Hash    : {sha256_hash}
Verification    : Integrity Verified (Demonstration Mode)

2. CORRELATION & ENTITY METRICS
--------------------------------------------------------------------------------
Total Entities Extracted    : {entities_count}
Relationships Identified     : {relationships_count}
Illustrative Explainable Risk Score : {risk_score}/100 ({risk_level})

3. KEY RISK SIGNALS DETECTED
--------------------------------------------------------------------------------
{signals_text}

4. HIGH-VALUE TARGET ENTITIES
--------------------------------------------------------------------------------
{", ".join(top_entities) if top_entities else "None"}

5. ANALYST RECOMMENDATIONS
--------------------------------------------------------------------------------
[!] Flagged IMEI & Shared IP nodes require further analyst review.
[!] Beneficiary UPI 'beneficiary_mule@okbank' linked across multiple bank accounts.
[!] Recommend manual verification of cross-linked artifact timestamps.

--------------------------------------------------------------------------------
DISCLAIMER: This is an automated analytical summary generated from synthetic demo evidence.
Illustrative Explainable Risk Score — Not Real Investigative Data — Not Legal Admissibility Proof.
================================================================================"""
    return brief