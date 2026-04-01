"""
Clause templates and trap definitions for contract generation.

Each contract type has a pool of normal clauses and a separate pool
of trap clauses.  The generator mixes them together based on the
requested difficulty.

Written to mirror real-world contract language — vague enough to be
tricky, specific enough to be analysable.
"""

# ─── trap catalogue ──────────────────────────────────────────────────
# Each trap has: type tag, severity (0-1), the sneaky clause text,
# a short explanation of why it's problematic, and a fair rewrite.

TRAP_CATALOGUE = {
    "unfair_termination": {
        "severity": 0.9,
        "text": (
            "Either party may terminate this agreement at any time, provided "
            "that the Client shall give thirty (30) days written notice, while "
            "the Service Provider may terminate immediately without cause or "
            "notice."
        ),
        "why_bad": (
            "Asymmetric termination rights — provider can leave instantly "
            "but the client is locked in with a 30-day notice period."
        ),
        "fair_version": (
            "Either party may terminate this agreement by giving thirty (30) "
            "days written notice to the other party."
        ),
    },
    "liability_shift": {
        "severity": 0.85,
        "text": (
            "The Service Provider shall not be liable for any direct, indirect, "
            "incidental, or consequential damages arising from the services, "
            "including but not limited to lost profits, data loss, or business "
            "interruption, regardless of negligence or fault."
        ),
        "why_bad": (
            "Blanket liability waiver protects the provider even when they are "
            "clearly at fault due to negligence."
        ),
        "fair_version": (
            "The Service Provider's total liability shall not exceed the fees "
            "paid under this agreement in the twelve (12) months preceding the "
            "claim.  This limitation does not apply in cases of gross negligence "
            "or wilful misconduct."
        ),
    },
    "vague_payment": {
        "severity": 0.7,
        "text": (
            "Payment terms shall be as mutually agreed upon from time to time.  "
            "Late payments may incur fees at the Provider's reasonable discretion."
        ),
        "why_bad": (
            "No concrete payment schedule or cap on late fees — leaves the "
            "client exposed to arbitrary charges."
        ),
        "fair_version": (
            "Invoices are due within thirty (30) days of receipt.  Late payments "
            "shall incur a fee of 1.5%% per month, compounding monthly, capped "
            "at 18%% per annum."
        ),
    },
    "hidden_auto_renewal": {
        "severity": 0.75,
        "text": (
            "This agreement shall automatically renew for successive one-year "
            "periods unless written notice of non-renewal is provided at least "
            "ninety (90) days prior to the end of the then-current term."
        ),
        "why_bad": (
            "90-day advance cancellation window is excessively long and easy "
            "to miss, effectively locking the client in."
        ),
        "fair_version": (
            "This agreement shall automatically renew for successive one-year "
            "periods unless either party provides written notice of non-renewal "
            "at least thirty (30) days prior to the end of the then-current term."
        ),
    },
    "non_compete_overreach": {
        "severity": 0.8,
        "text": (
            "For a period of twenty-four (24) months following termination, "
            "the Client shall not engage, directly or indirectly, with any "
            "competing service provider offering similar services anywhere "
            "in the world."
        ),
        "why_bad": (
            "Overly broad non-compete: 2-year global restriction is "
            "unreasonable and likely unenforceable in many jurisdictions, "
            "but still chilling."
        ),
        "fair_version": (
            "For a period of six (6) months following termination, the "
            "Client shall not solicit the Provider's employees or direct "
            "contractors who were involved in delivering services."
        ),
    },
    "ip_grab": {
        "severity": 0.95,
        "text": (
            "All intellectual property, ideas, inventions, and work product "
            "conceived or developed by the Client during the term of this "
            "agreement, whether or not related to the services, shall be the "
            "sole and exclusive property of the Service Provider."
        ),
        "why_bad": (
            "Sweeping IP assignment that captures even unrelated client work — "
            "far beyond what's reasonably connected to the engagement."
        ),
        "fair_version": (
            "Work product created specifically under this agreement and "
            "directly related to the services shall be jointly owned.  "
            "All pre-existing IP remains with its original owner."
        ),
    },
    "unilateral_amendment": {
        "severity": 0.8,
        "text": (
            "The Service Provider reserves the right to modify the terms of "
            "this agreement at any time by posting updated terms on its website.  "
            "Continued use of the services constitutes acceptance of modified terms."
        ),
        "why_bad": (
            "Provider can change the deal unilaterally without explicit consent — "
            "the client may not even be aware of changes."
        ),
        "fair_version": (
            "Any amendment to this agreement must be in writing and signed "
            "by both parties to be effective."
        ),
    },
    "forced_arbitration": {
        "severity": 0.65,
        "text": (
            "Any dispute arising out of this agreement shall be resolved "
            "exclusively through binding arbitration administered by an "
            "arbitration body selected solely by the Service Provider, with "
            "proceedings conducted in a jurisdiction of the Provider's choosing."
        ),
        "why_bad": (
            "Provider picks the arbitrator and the location — strips the client "
            "of meaningful dispute resolution options."
        ),
        "fair_version": (
            "Disputes shall be resolved through binding arbitration under "
            "the rules of a mutually agreed-upon arbitration body, with "
            "proceedings in a location convenient to both parties."
        ),
    },
}


# ─── fair clause pools (per contract type) ───────────────────────────
# These are perfectly fine clauses with no traps.

FAIR_CLAUSES = {
    "freelance": [
        {
            "title": "Scope of Work",
            "body": (
                "The Contractor agrees to perform the services described in "
                "Exhibit A attached hereto.  Any work outside the defined scope "
                "requires a written change order signed by both parties."
            ),
            "fairness": 0.95,
        },
        {
            "title": "Payment Schedule",
            "body": (
                "The Client shall pay the Contractor within thirty (30) days "
                "of receiving a valid invoice.  The hourly rate is as stated in "
                "Schedule B.  Expenses exceeding $100 require pre-approval."
            ),
            "fairness": 0.90,
        },
        {
            "title": "Confidentiality",
            "body": (
                "Both parties agree to keep confidential any proprietary "
                "information disclosed during the engagement.  This obligation "
                "survives termination for a period of two (2) years."
            ),
            "fairness": 0.92,
        },
        {
            "title": "Delivery Timeline",
            "body": (
                "Milestones and deadlines are specified in Exhibit A.  If "
                "delivery is delayed by more than fourteen (14) business days, "
                "either party may renegotiate the timeline in good faith."
            ),
            "fairness": 0.88,
        },
        {
            "title": "Indemnification",
            "body": (
                "Each party shall indemnify and hold the other harmless from "
                "claims arising out of its own negligence or breach of this "
                "agreement."
            ),
            "fairness": 0.90,
        },
    ],

    "lease": [
        {
            "title": "Premises Description",
            "body": (
                "The Landlord leases to the Tenant the commercial unit at "
                "the address specified in Schedule 1, including all fixtures "
                "and fittings listed in the inventory."
            ),
            "fairness": 0.95,
        },
        {
            "title": "Rent and Deposit",
            "body": (
                "Monthly rent is payable on the first business day of each "
                "month.  A refundable security deposit equal to two months' "
                "rent is due upon execution of this lease."
            ),
            "fairness": 0.90,
        },
        {
            "title": "Maintenance Responsibilities",
            "body": (
                "The Landlord shall maintain structural components and common "
                "areas.  The Tenant shall maintain the interior and report "
                "any damage within seventy-two (72) hours of occurrence."
            ),
            "fairness": 0.88,
        },
        {
            "title": "Use of Premises",
            "body": (
                "The Tenant shall use the premises solely for the purposes "
                "stated in Schedule 2.  Sub-letting requires prior written "
                "consent of the Landlord, not to be unreasonably withheld."
            ),
            "fairness": 0.92,
        },
        {
            "title": "Insurance",
            "body": (
                "The Tenant shall maintain comprehensive liability insurance "
                "with a minimum coverage amount specified in Schedule 3 for "
                "the duration of the lease."
            ),
            "fairness": 0.90,
        },
    ],

    "vendor": [
        {
            "title": "Service Level Agreement",
            "body": (
                "The Vendor guarantees 99.5%% uptime for the services measured "
                "on a monthly basis.  Credits shall be issued for downtime "
                "exceeding the guaranteed level as described in Exhibit C."
            ),
            "fairness": 0.92,
        },
        {
            "title": "Data Handling",
            "body": (
                "The Vendor shall process Client data solely for the purpose "
                "of providing the contracted services.  Data shall be encrypted "
                "at rest and in transit using industry-standard protocols."
            ),
            "fairness": 0.94,
        },
        {
            "title": "Support and Escalation",
            "body": (
                "Technical support is available 9 AM to 6 PM on business days.  "
                "Critical issues are acknowledged within two (2) hours and "
                "resolved within eight (8) hours on a best-effort basis."
            ),
            "fairness": 0.88,
        },
        {
            "title": "Contract Duration",
            "body": (
                "This agreement runs for an initial term of twelve (12) months "
                "from the effective date and may be renewed by mutual written "
                "agreement at least thirty (30) days before expiry."
            ),
            "fairness": 0.90,
        },
        {
            "title": "Compliance",
            "body": (
                "Both parties shall comply with all applicable laws, "
                "regulations, and industry standards relevant to the services "
                "provided under this agreement."
            ),
            "fairness": 0.95,
        },
    ],
}


# ─── trap-to-title mapping (so traps blend in naturally) ─────────────

TRAP_TITLES = {
    "unfair_termination": "Termination",
    "liability_shift": "Limitation of Liability",
    "vague_payment": "Payment Terms",
    "hidden_auto_renewal": "Term and Renewal",
    "non_compete_overreach": "Non-Competition",
    "ip_grab": "Intellectual Property",
    "unilateral_amendment": "Amendment",
    "forced_arbitration": "Dispute Resolution",
}
