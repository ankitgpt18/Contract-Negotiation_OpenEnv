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
    "data_monetization": {
        "severity": 0.88,
        "text": (
            "The Provider reserves the right to anonymize and aggregate Customer "
            "data for internal analytics and research purposes.  The Provider may "
            "share this data with third-party partners and vendors for commercial purposes."
        ),
        "why_bad": (
            "Provider can monetize customer data without explicit consent or benefit "
            "sharing — effectively using customer data as a product."
        ),
        "fair_version": (
            "Customer data shall not be used for any purpose beyond providing the "
            "contracted services without explicit prior written consent.  Anonymized "
            "usage statistics may be retained for service improvement."
        ),
    },
    "unilateral_price_increase": {
        "severity": 0.82,
        "text": (
            "The Provider may increase subscription fees at any time with written "
            "notice to the Customer.  Continued use of the platform constitutes "
            "acceptance of the new pricing."
        ),
        "why_bad": (
            "Provider can raise prices unilaterally with no cap or renewal anchor, "
            "forcing customers to accept or leave."
        ),
        "fair_version": (
            "Pricing changes apply only upon renewal of the subscription term.  "
            "The Provider shall provide ninety (90) days' notice of any price increases "
            "exceeding five percent (5%%) per annum."
        ),
    },
    "indemnity_overreach": {
        "severity": 0.78,
        "text": (
            "The Buyer shall indemnify the Seller against any claim, loss, or "
            "liability arising from any event occurring before, during, or after "
            "the closing of the transaction, including unforeseeable future claims."
        ),
        "why_bad": (
            "Indemnification window is unlimited in time and scope — the Seller "
            "has perpetual protection while the Buyer carries unlimited risk."
        ),
        "fair_version": (
            "Each party shall indemnify the other against breaches of representations "
            "and warranties for a period of eighteen (18) months post-closing, "
            "subject to a materiality threshold of fifty thousand dollars ($50,000)."
        ),
    },
    "escrow_forfeiture": {
        "severity": 0.80,
        "text": (
            "Any funds remaining in escrow at the end of the holdback period that "
            "have not been claimed shall be forfeited to the Seller.  No funds "
            "shall be released to the Buyer under any circumstances."
        ),
        "why_bad": (
            "Escrow structure is one-sided — unfair claims are forfeited to the "
            "Seller rather than returned to the Buyer."
        ),
        "fair_version": (
            "Any unclaimed escrow funds remaining at the end of the holdback period "
            "shall be returned to the Buyer.  The Seller may submit indemnification "
            "claims within thirty (30) days before the release."
        ),
    },
    "license_clawback": {
        "severity": 0.85,
        "text": (
            "The Licensor retains the right to terminate this license at any time "
            "without cause and without refund.  Upon termination, all licensed "
            "materials must be destroyed immediately and all existing products "
            "must be removed from distribution."
        ),
        "why_bad": (
            "Licensor can revoke license unilaterally, destroying the Licensee's "
            "entire business with no recourse or wind-down period."
        ),
        "fair_version": (
            "Either party may terminate for material breach with ninety (90) days' "
            "cure period.  Upon termination without cause, the Licensee has one hundred "
            "eighty (180) days to wind down existing products and sell remaining inventory."
        ),
    },
    "field_of_use_restriction": {
        "severity": 0.72,
        "text": (
            "The licensed IP may only be used in the exact field of use specified "
            "in Exhibit A.  Any deviation or extension of use requires renegotiation "
            "of the license terms and additional fees determined at the Licensor's sole discretion."
        ),
        "why_bad": (
            "Overly restrictive field-of-use clause limits licensee's business "
            "flexibility and gives licensor unilateral pricing power for expansions."
        ),
        "fair_version": (
            "The licensed IP may be used in [specified field] and reasonable extensions "
            "thereof.  Significant new applications require mutual written agreement, "
            "with pricing to be determined in good faith within thirty (30) days."
        ),
    },
    "non_compete_employment": {
        "severity": 0.75,
        "text": (
            "During employment and for three (3) years following termination, "
            "the Employee shall not engage in any business substantially similar "
            "to the Employer's, including consulting, employment, or board service "
            "with any competitor in any geographic location."
        ),
        "why_bad": (
            "Three-year global non-compete is excessively broad and likely "
            "unenforceable, but creates a chilling effect on any future opportunity."
        ),
        "fair_version": (
            "For six (6) months following voluntary termination, the Employee shall "
            "not solicit the Employer's customers known to the Employee.  Geographic "
            "and role restrictions are limited to the Employee's last assigned territory."
        ),
    },
    "wage_clawback": {
        "severity": 0.88,
        "text": (
            "If the Employee engages in any corporate malfeasance, misuse of company "
            "assets, or violation of any company policy at any time during employment, "
            "the Employer may recover all compensation paid, including salary, bonuses, "
            "and benefits, for the preceding twelve (12) months."
        ),
        "why_bad": (
            "Retroactive clawback of all compensation for vague violations leaves "
            "employee exposed to financial ruin for minor infractions."
        ),
        "fair_version": (
            "Gross negligence or deliberate policy violations may result in forfeiture "
            "of the current month's bonus only, subject to written notice and ten (10) "
            "business days for the Employee to cure or dispute."
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

    "saas": [
        {
            "title": "Service Availability",
            "body": (
                "The Provider commits to maintaining the platform with ninety-nine "
                "percent (99%%) uptime, measured monthly.  Scheduled maintenance "
                "windows of up to four (4) hours per month are excluded."
            ),
            "fairness": 0.91,
        },
        {
            "title": "Data Ownership and Access",
            "body": (
                "The Customer retains full ownership of all data uploaded to the "
                "platform.  The Customer may export or delete data at any time "
                "subject to a thirty (30) day retention period for backup purposes."
            ),
            "fairness": 0.93,
        },
        {
            "title": "Security Standards",
            "body": (
                "The Provider shall maintain SOC 2 Type II certification and "
                "perform annual third-party security audits.  Results shall be "
                "made available to the Customer upon request."
            ),
            "fairness": 0.94,
        },
        {
            "title": "Acceptable Use Policy",
            "body": (
                "The Customer agrees not to use the service for unlawful purposes, "
                "malware distribution, or to circumvent pricing tiers.  Violations "
                "may result in account suspension with thirty (30) days' notice."
            ),
            "fairness": 0.89,
        },
        {
            "title": "Billing and Invoicing",
            "body": (
                "Fees are charged monthly based on usage or fixed tier selection.  "
                "Invoices are issued on the first day of each month and are due "
                "within fifteen (15) days.  Price increases require sixty (60) days' notice."
            ),
            "fairness": 0.90,
        },
    ],

    "ma": [
        {
            "title": "Representations and Warranties",
            "body": (
                "The Seller represents that it has full authority to enter into "
                "this transaction, all financial statements are accurate and "
                "complete, and there are no undisclosed liabilities."
            ),
            "fairness": 0.93,
        },
        {
            "title": "Purchase Price and Adjustment",
            "body": (
                "The total purchase price is $[Amount], subject to post-closing "
                "adjustment for working capital.  Any variance exceeding ten percent "
                "(10%%) shall entitle either party to renegotiate the price within "
                "ninety (90) days of closing."
            ),
            "fairness": 0.91,
        },
        {
            "title": "Escrow and Holdback",
            "body": (
                "Twenty percent (20%%) of the purchase price shall be deposited "
                "in escrow for eighteen (18) months to secure indemnification "
                "obligations.  Remaining amounts shall be released upon expiration "
                "of the indemnification period absent pending claims."
            ),
            "fairness": 0.92,
        },
        {
            "title": "Due Diligence and Inspection",
            "body": (
                "The Buyer has the right to conduct reasonable due diligence for "
                "a period of forty-five (45) days, including access to books, "
                "records, and meetings with key personnel."
            ),
            "fairness": 0.94,
        },
        {
            "title": "Transition Services",
            "body": (
                "The Seller shall provide transition support for sixty (60) days "
                "post-closing at a mutually agreed hourly rate of $[Rate].  Extended "
                "support is available at the same rate if agreed in writing."
            ),
            "fairness": 0.88,
        },
    ],

    "ip_license": [
        {
            "title": "License Grant",
            "body": (
                "The Licensor grants a non-exclusive, royalty-free license to use "
                "the intellectual property for the purposes specified in Exhibit A.  "
                "The license may not be sublicensed or transferred without written consent."
            ),
            "fairness": 0.92,
        },
        {
            "title": "Term and Renewal",
            "body": (
                "This license is granted for an initial term of three (3) years from "
                "the effective date and shall automatically renew for successive one-year "
                "periods unless either party provides ninety (90) days' prior notice."
            ),
            "fairness": 0.90,
        },
        {
            "title": "Quality Control",
            "body": (
                "The Licensee shall maintain quality standards consistent with the "
                "Licensor's brand guidelines, which shall be provided in writing.  "
                "The Licensor may audit compliance with reasonable notice."
            ),
            "fairness": 0.88,
        },
        {
            "title": "Royalty Payments",
            "body": (
                "The Licensee shall pay royalties equal to five percent (5%%) of "
                "net sales, due within thirty (30) days of each quarter-end.  The "
                "Licensor shall have the right to audit royalty records annually."
            ),
            "fairness": 0.91,
        },
        {
            "title": "Improvements and Feedback",
            "body": (
                "Any improvements made by the Licensee to the licensed IP shall be "
                "owned jointly.  The Licensee grants the Licensor a royalty-free "
                "license to incorporate such improvements in future versions."
            ),
            "fairness": 0.89,
        },
    ],

    "employment": [
        {
            "title": "Position and Duties",
            "body": (
                "The Employee shall be employed as [Job Title] with responsibilities "
                "as described in the job specification.  Duties may be modified by "
                "mutual agreement or with thirty (30) days' written notice."
            ),
            "fairness": 0.90,
        },
        {
            "title": "Compensation and Benefits",
            "body": (
                "The Employee shall receive an annual salary of $[Amount] payable "
                "bi-weekly, plus standard benefits including health insurance, "
                "401(k) matching at six percent (6%%), and twenty (20) days PTO annually."
            ),
            "fairness": 0.92,
        },
        {
            "title": "At-Will Employment",
            "body": (
                "Employment is at-will, meaning either party may terminate the "
                "relationship at any time with two (2) weeks' written notice, except "
                "in cases of termination for cause, which requires immediate severance."
            ),
            "fairness": 0.88,
        },
        {
            "title": "Confidentiality and Trade Secrets",
            "body": (
                "The Employee shall maintain confidentiality of proprietary information "
                "during and after employment for two (2) years.  This obligation does "
                "not apply to information that becomes publicly available."
            ),
            "fairness": 0.91,
        },
        {
            "title": "Workplace Conduct",
            "body": (
                "The Employee agrees to follow all company policies, report to the "
                "designated manager, and maintain professional conduct at all times.  "
                "Policy violations may result in disciplinary action up to termination."
            ),
            "fairness": 0.87,
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
    "data_monetization": "Data Rights",
    "unilateral_price_increase": "Pricing",
    "indemnity_overreach": "Indemnification",
    "escrow_forfeiture": "Escrow Terms",
    "license_clawback": "License Termination",
    "field_of_use_restriction": "Field of Use",
    "non_compete_employment": "Non-Compete",
    "wage_clawback": "Compensation Clawback",
}
