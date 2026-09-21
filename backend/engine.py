import re
import pandas as pd

from typing import List, Dict, Any, Tuple

from backend.models import (
    Entity,
    Relationship,
    Signal,
    RiskAssessment,
    TimelineEvent
)


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def normalize_value(val: Any) -> str:
    """
    Convert values to clean strings.

    Important:
    CSV identifiers such as phone numbers, IMEI and IMSI can
    sometimes be read by pandas as floats, producing values like
    919876543210.0. This function removes that unwanted .0.
    """
    if val is None or pd.isna(val):
        return ""

    # Remove .0 when pandas has interpreted an integer-like value
    # as a floating-point number.
    if isinstance(val, float) and val.is_integer():
        return str(int(val))

    return str(val).strip()


def normalize_phone(phone: str) -> str:
    phone = normalize_value(phone)

    if not phone:
        return ""

    digits = re.sub(r"\D", "", phone)

    if len(digits) == 10:
        return f"+91{digits}"

    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"

    return phone


def normalize_ip(ip: str) -> str:
    return normalize_value(ip).lower()


def normalize_upi(upi: str) -> str:
    return normalize_value(upi).lower()


def normalize_email(email: str) -> str:
    return normalize_value(email).lower()


def normalize_identifier(value: Any) -> str:
    """
    Used for IMEI, IMSI, bank account and transaction identifiers.
    """
    return normalize_value(value)


# ============================================================
# DATA PROCESSING
# ============================================================

def process_evidence_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize all important evidence fields before analysis.
    """

    clean_df = df.copy()

    columns = [
        "phone",
        "imei",
        "imsi",
        "upi_id",
        "bank_account",
        "transaction_id",
        "ip_address",
        "email"
    ]

    # Make sure all expected columns exist.
    for col in columns:
        if col not in clean_df.columns:
            clean_df[col] = ""
        else:
            clean_df[col] = clean_df[col].fillna("")

    # Normalize fields.
    clean_df["phone"] = clean_df["phone"].apply(normalize_phone)
    clean_df["imei"] = clean_df["imei"].apply(normalize_identifier)
    clean_df["imsi"] = clean_df["imsi"].apply(normalize_identifier)

    clean_df["upi_id"] = clean_df["upi_id"].apply(normalize_upi)

    clean_df["bank_account"] = clean_df["bank_account"].apply(
        normalize_identifier
    )

    clean_df["transaction_id"] = clean_df["transaction_id"].apply(
        normalize_identifier
    )

    clean_df["ip_address"] = clean_df["ip_address"].apply(normalize_ip)
    clean_df["email"] = clean_df["email"].apply(normalize_email)

    return clean_df


# ============================================================
# ENTITY + RELATIONSHIP EXTRACTION
# ============================================================

def extract_entities_and_relationships(
    df: pd.DataFrame
) -> Tuple[List[Entity], List[Relationship], List[TimelineEvent]]:

    entities_map: Dict[str, Entity] = {}
    relationships_map: Dict[str, Relationship] = {}
    timeline: List[TimelineEvent] = []

    def get_entity_id(entity_type: str, value: str) -> str:
        return f"{entity_type}:{value}"

    records = df.to_dict("records")

    for idx, row in enumerate(records):

        evidence_id = str(
            row.get("evidence_id", f"EV-{idx + 1}")
        )

        source = str(
            row.get("source", "LOG")
        )

        event_type = str(
            row.get("event_type", "EVENT")
        )

        timestamp = str(
            row.get("timestamp", "")
        )

        # ----------------------------------------------------
        # Timeline
        # ----------------------------------------------------

        description = (
            f"Source: {source} | Event: {event_type}"
        )

        amount_value = row.get("amount", "")

        try:
            if amount_value not in ("", None) and not pd.isna(amount_value):
                amount = float(amount_value)

                if amount > 0:
                    if amount.is_integer():
                        amount_text = str(int(amount))
                    else:
                        amount_text = str(amount)

                    description += f" | Amount: ₹{amount_text}"

        except (ValueError, TypeError):
            pass

        timeline.append(
            TimelineEvent(
                timestamp=timestamp,
                event_type=event_type,
                source=source,
                evidence_id=evidence_id,
                description=description
            )
        )

        # ----------------------------------------------------
        # Extract entities
        # ----------------------------------------------------

        row_entities: Dict[str, Entity] = {}

        fields = [
            ("PHONE", row.get("phone", "")),
            ("IMEI", row.get("imei", "")),
            ("IMSI", row.get("imsi", "")),
            ("UPI", row.get("upi_id", "")),
            ("BANK", row.get("bank_account", "")),
            ("TXN", row.get("transaction_id", "")),
            ("IP", row.get("ip_address", "")),
            ("EMAIL", row.get("email", ""))
        ]

        for entity_type, entity_value in fields:

            entity_value = normalize_value(entity_value)

            if not entity_value:
                continue

            entity_id = get_entity_id(
                entity_type,
                entity_value
            )

            if entity_id not in entities_map:

                entities_map[entity_id] = Entity(
                    id=entity_id,
                    type=entity_type,
                    value=entity_value
                )

            row_entities[entity_type] = entities_map[entity_id]

        # ----------------------------------------------------
        # Meaningful forensic relationships
        #
        # Instead of connecting every entity to every other
        # entity, only meaningful evidence relationships are
        # created.
        # ----------------------------------------------------

        relationship_pairs = [
            ("PHONE", "IMEI"),
            ("PHONE", "IMSI"),
            ("PHONE", "IP"),
            ("PHONE", "UPI"),
            ("PHONE", "EMAIL"),
            ("UPI", "BANK"),
            ("BANK", "TXN"),
            ("EMAIL", "IP"),
            ("IP", "IMEI")
        ]

        for type_a, type_b in relationship_pairs:

            entity_a = row_entities.get(type_a)
            entity_b = row_entities.get(type_b)

            if not entity_a or not entity_b:
                continue

            # Keep relationship ordering deterministic.
            if entity_a.id > entity_b.id:
                entity_a, entity_b = entity_b, entity_a

            relationship_key = (
                f"{entity_a.id}----{entity_b.id}"
            )

            relationship_type = (
                f"{entity_a.type}_LINKED_{entity_b.type}"
            )

            if relationship_key in relationships_map:

                relationship = relationships_map[
                    relationship_key
                ]

                if evidence_id not in relationship.evidence_ids:
                    relationship.evidence_ids.append(
                        evidence_id
                    )

            else:

                relationships_map[relationship_key] = Relationship(
                    source=entity_a.id,
                    target=entity_b.id,
                    relationship=relationship_type,
                    evidence_ids=[evidence_id]
                )

    # Sort timeline chronologically.
    timeline.sort(
        key=lambda event: event.timestamp
    )

    return (
        list(entities_map.values()),
        list(relationships_map.values()),
        timeline
    )

# ============================================================
# EXPLAINABLE CORRELATION RULES
# ============================================================

def evaluate_correlation_rules(
    entities: List[Entity],
    relationships: List[Relationship],
    df: pd.DataFrame
) -> RiskAssessment:

    signals: List[Signal] = []
    total_score = 0
    suspicious_entities = set()

    records = df.to_dict("records")

    # ========================================================
    # RULE 1
    # Same IMEI connected to multiple phone numbers
    # +30
    #
    # Important:
    # Rule score is added ONLY ONCE even if multiple
    # suspicious IMEI groups are found.
    # ========================================================

    imei_to_phones: Dict[str, set] = {}

    for row in records:
        imei = normalize_value(row.get("imei", ""))
        phone = normalize_phone(row.get("phone", ""))

        if imei and phone:
            imei_to_phones.setdefault(imei, set()).add(phone)

    rule1_triggered = False
    rule1_entities = []

    for imei, phones in imei_to_phones.items():

        if len(phones) > 1:

            rule1_triggered = True

            affected = (
                [f"IMEI:{imei}"]
                + [f"PHONE:{phone}" for phone in sorted(phones)]
            )

            rule1_entities.extend(affected)
            suspicious_entities.update(affected)

    if rule1_triggered:

        total_score += 30

        # Remove duplicate entities while preserving order
        rule1_entities = list(dict.fromkeys(rule1_entities))

        signals.append(
            Signal(
                rule_id="RULE_1_MULTI_IMEI",
                name="Same IMEI Used by Multiple Phones",
                weight=30,
                description=(
                    "One or more IMEI identifiers were observed "
                    "with multiple distinct phone numbers."
                ),
                affected_entities=rule1_entities
            )
        )

    # ========================================================
    # RULE 2
    # Shared IP across multiple phones
    # +15
    #
    # Score added ONLY ONCE.
    # ========================================================

    ip_to_phones: Dict[str, set] = {}

    for row in records:
        ip_address = normalize_ip(row.get("ip_address", ""))
        phone = normalize_phone(row.get("phone", ""))

        if ip_address and phone:
            ip_to_phones.setdefault(ip_address, set()).add(phone)

    rule2_triggered = False
    rule2_entities = []

    for ip_address, phones in ip_to_phones.items():

        if len(phones) > 1:

            rule2_triggered = True

            affected = (
                [f"IP:{ip_address}"]
                + [f"PHONE:{phone}" for phone in sorted(phones)]
            )

            rule2_entities.extend(affected)
            suspicious_entities.update(affected)

    if rule2_triggered:

        total_score += 15

        rule2_entities = list(dict.fromkeys(rule2_entities))

        signals.append(
            Signal(
                rule_id="RULE_2_SHARED_IP",
                name="Shared IP Across Multiple Phones",
                weight=15,
                description=(
                    "One or more IP addresses were observed "
                    "across multiple distinct phone numbers."
                ),
                affected_entities=rule2_entities
            )
        )

    # ========================================================
    # RULE 3
    # Same UPI connected to multiple bank accounts
    # +25
    #
    # Score added ONLY ONCE.
    # ========================================================

    upi_to_banks: Dict[str, set] = {}

    for row in records:
        upi = normalize_upi(row.get("upi_id", ""))
        bank = normalize_identifier(row.get("bank_account", ""))

        if upi and bank:
            upi_to_banks.setdefault(upi, set()).add(bank)

    rule3_triggered = False
    rule3_entities = []

    for upi, banks in upi_to_banks.items():

        if len(banks) > 1:

            rule3_triggered = True

            affected = (
                [f"UPI:{upi}"]
                + [f"BANK:{bank}" for bank in sorted(banks)]
            )

            rule3_entities.extend(affected)
            suspicious_entities.update(affected)

    if rule3_triggered:

        total_score += 25

        rule3_entities = list(dict.fromkeys(rule3_entities))

        signals.append(
            Signal(
                rule_id="RULE_3_MULTI_BANK_UPI",
                name="UPI Beneficiary Linked to Multiple Bank Accounts",
                weight=25,
                description=(
                    "One or more UPI identifiers were linked "
                    "to multiple bank accounts."
                ),
                affected_entities=rule3_entities
            )
        )

    # ========================================================
    # RULE 4
    # Same phone associated with multiple IMSIs
    # +25
    #
    # Score added ONLY ONCE.
    # ========================================================

    phone_to_imsis: Dict[str, set] = {}

    for row in records:
        phone = normalize_phone(row.get("phone", ""))
        imsi = normalize_identifier(row.get("imsi", ""))

        if phone and imsi:
            phone_to_imsis.setdefault(phone, set()).add(imsi)

    rule4_triggered = False
    rule4_entities = []

    for phone, imsis in phone_to_imsis.items():

        if len(imsis) > 1:

            rule4_triggered = True

            affected = (
                [f"PHONE:{phone}"]
                + [f"IMSI:{imsi}" for imsi in sorted(imsis)]
            )

            rule4_entities.extend(affected)
            suspicious_entities.update(affected)

    if rule4_triggered:

        total_score += 25

        rule4_entities = list(dict.fromkeys(rule4_entities))

        signals.append(
            Signal(
                rule_id="RULE_4_MULTI_IMSI",
                name="Multiple IMSIs Observed for Single Phone",
                weight=25,
                description=(
                    "One or more phone numbers were associated "
                    "with multiple IMSI identities."
                ),
                affected_entities=rule4_entities
            )
        )

    # ========================================================
    # FINAL SCORE
    #
    # Maximum possible:
    #
    # 30 + 15 + 25 + 25 = 95
    #
    # Each rule contributes at most once.
    # ========================================================

    final_score = total_score

    # ========================================================
    # Risk classification
    # ========================================================

    if final_score >= 70:
        level = "ILLUSTRATIVE HIGH-RISK CLUSTER"
    elif final_score >= 40:
        level = "ILLUSTRATIVE MEDIUM-RISK CLUSTER"
    else:
        level = "ILLUSTRATIVE LOW-RISK CLUSTER"

    # ========================================================
    # Mark relationships connected to suspicious entities
    # ========================================================

    for relationship in relationships:

        if (
            relationship.source in suspicious_entities
            or relationship.target in suspicious_entities
        ):
            relationship.is_suspicious = True

    return RiskAssessment(
        score=final_score,
        level=level,
        signals=signals
    )