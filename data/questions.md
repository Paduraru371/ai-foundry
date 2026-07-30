# Onboarding evaluation question set

## Evaluation setup

This file contains 15 evaluation questions for the onboarding knowledge corpus.

The recorded answers below represent an initial **single-pass retrieval baseline**:

- retrieval method: one lexical retrieval pass;
- generation rule: answer only from the retrieved document;
- version handling: no dedicated metadata filter;
- multi-step handling: no automatic second search;
- unsupported-answer policy: refuse when no supporting statement is found.

This baseline is intentionally limited. It provides a useful comparison point for later metadata filtering, multi-document retrieval, arithmetic tools, and agentic search.

## Result summary

| Group | Correct | Wrong | Refused correctly | Refused when answer existed |
|---|---:|---:|---:|---:|
| A — Simple retrieval | 6 | 1 | 0 | 0 |
| B — Multi-step | 3 | 2 | 0 | 0 |
| C — Must refuse | 0 | 0 | 3 | 0 |
| **Total** | **9** | **3** | **3** | **0** |

Overall acceptable outcomes: **12/15**.

The three failures are useful:

1. the retriever selected the superseded 2025 retry policy for a 2026 question;
2. the business-fee question was answered without checking online eligibility;
3. the version-comparison question used only the historical document and omitted the 2026 values.

---

# A — Simple retrieval

## A1. Video-identification attempts in 2026

**Question**

How many video-identification attempts are allowed within 24 hours for an application started on 10 February 2026?

**Expected answer**

A maximum of **3 attempts within 24 hours**. After three unsuccessful attempts, identification is blocked for 24 hours from the last attempt.

**Source documents**

- `19_identification_retries_2026.md`

**Actual assistant answer**

A maximum of **5 video-identification attempts within 24 hours** is permitted. After five unsuccessful attempts, identification is blocked for 24 hours. `[Identification retries and application expiry, effective 2025-01-01, version 2]`

**Outcome**

`wrong`

**Observation**

The lexical retriever ranked the near-duplicate 2025 document above the active 2026 version. A metadata filter using `status`, `effective`, and the application date should prevent this error.

---

## A2. Application validity in 2026

**Question**

For how many calendar days does an onboarding application started after 15 January 2026 remain active?

**Expected answer**

The application remains active for **15 calendar days** from the date it is started.

**Source documents**

- `19_identification_retries_2026.md`

**Actual assistant answer**

The application remains active for **15 calendar days** from the start date. Additional requests do not automatically extend this period. `[Identification retries and application expiry, effective 2026-01-15, version 3]`

**Outcome**

`correct`

---

## A3. Personal foreign-document review fee

**Question**

What is the 2026 fee for reviewing one foreign-language document during personal onboarding?

**Expected answer**

The fee is **75 lei for each document**, provided that the bank accepts the document for review without requiring an authorised translation.

**Source documents**

- `08_personal_onboarding_fees_2026.md`

**Actual assistant answer**

The fee is **75 lei per document**. Authorised translations, legalisation, and apostilles are not included. `[Personal onboarding fees, effective 2026-01-15, version 3]`

**Outcome**

`correct`

---

## A4. First manual-review time

**Question**

How long can the first manual review take once all requested documents have been supplied?

**Expected answer**

The first manual review takes no more than **2 working days** from the moment all requested documents are available. The period is paused while the bank is waiting for the applicant.

**Source documents**

- `05_manual_review_and_processing_times.md`

**Actual assistant answer**

The standard time for the first manual review is no more than **2 working days** after all requested documents have been supplied. `[Manual review, processing times, and additional requests, effective 2026-01-15, version 4]`

**Outcome**

`correct`

---

## A5. Proof of address

**Question**

Which documents may be used as proof of address when the identity document does not show the address?

**Expected answer**

A bank statement, utility bill, residence certificate, or document issued by a public authority may be accepted if it was issued within the previous **90 days** and shows the applicant's full name and address.

**Source documents**

- `02_accepted_documents_for_individuals.md`

**Actual assistant answer**

Accepted evidence includes a bank statement, utility bill, residence certificate, or public-authority document issued within the previous **90 days**, provided that the full name and address are visible. `[Accepted documents for personal onboarding, effective 2026-02-01, version 3]`

**Outcome**

`correct`

---

## A6. Initial deposit

**Question**

Is an initial deposit required to activate a standard personal account?

**Expected answer**

No. An initial deposit is not required for activation, although operations involving payments or fees require sufficient funds.

**Source documents**

- `06_account_activation_and_mobile_banking.md`

**Actual assistant answer**

No. The standard personal account can be activated without an initial deposit. Functions involving a payment or fee require sufficient funds. `[Account activation and mobile banking access, effective 2026-02-20, version 3]`

**Outcome**

`correct`

---

## A7. Beneficial-owner ownership threshold

**Question**

What ownership threshold requires an individual to be declared as a beneficial owner in the standard business flow?

**Expected answer**

Every individual who directly or indirectly holds **more than 20%** of the capital or voting rights must be declared. Control through other means must also be declared even when the percentage threshold is not exceeded.

**Source documents**

- `11_beneficial_owner_and_ownership_structure.md`

**Actual assistant answer**

Individuals holding **more than 20%**, directly or indirectly, of the capital or voting rights must be declared. Control through other means may also qualify. `[Identification of the beneficial owner and ownership structure, effective 2026-01-15, version 5]`

**Outcome**

`correct`

---

# B — Multi-step

## B1. Two foreign documents and paper confirmation

**Question**

A personal applicant starts an application in March 2026, submits two foreign-language documents for review, and requests a paper account confirmation. What is the total onboarding fee?

**Expected answer**

The total is **170 lei**:

- 2 × 75 lei for the foreign-language documents = 150 lei;
- 20 lei for the paper account confirmation;
- total: 150 lei + 20 lei = **170 lei**.

This assumes that the documents can be reviewed without authorised translations.

**Source documents**

- `08_personal_onboarding_fees_2026.md`

**What makes it hard**

The assistant must select the 2026 schedule, extract two different table rows, multiply a per-document fee, and add the results.

**Actual assistant answer**

The total is **170 lei**: 150 lei for two foreign-language documents and 20 lei for the paper confirmation. The cost of any required authorised translation is separate. `[Personal onboarding fees, effective 2026-01-15, version 3]`

**Outcome**

`correct`

---

## B2. SRL Start eligibility and total onboarding fee

**Question**

An active Romanian SRL Start has one legal representative who can act independently, two additional representatives, one foreign document to review, and requires card delivery. Is it normally eligible for online onboarding, and what is the total listed onboarding fee?

**Expected answer**

It is normally eligible for online onboarding if its public-register data is current, its ownership can be declared, its activity is permitted, and the legal representative has sufficient authority. Final approval is not guaranteed.

The listed fee is **140 lei**:

- standard opening: 0 lei;
- two additional representatives: 2 × 20 lei = 40 lei;
- one foreign document: 75 lei;
- card delivery: 25 lei;
- total: **140 lei**.

**Source documents**

- `09_online_business_account_eligibility.md`
- `13_business_onboarding_fees_2026.md`

**What makes it hard**

The assistant must first check eligibility in one document, then retrieve a table from another document and perform arithmetic.

**Actual assistant answer**

The total onboarding fee is **140 lei**: 40 lei for two additional representatives, 75 lei for one foreign document, and 25 lei for card delivery. `[Business onboarding fees, effective 2026-01-15, version 3]`

**Outcome**

`wrong`

**Observation**

The fee calculation was correct, but the answer did not address eligibility or explain that technical eligibility does not guarantee approval. A second retrieval was needed.

---

## B3. Compare the 2025 and 2026 retry policies

**Question**

Compare the retry limit and application-validity period for an application started in December 2025 with one started in February 2026.

**Expected answer**

- December 2025: maximum **5 attempts in 24 hours** and an application-validity period of **30 calendar days**.
- February 2026: maximum **3 attempts in 24 hours** and an application-validity period of **15 calendar days**.
- The new values took effect on **15 January 2026**.

**Source documents**

- `18_identification_retries_2025.md`
- `19_identification_retries_2026.md`

**What makes it hard**

The answer requires retrieval of two near-duplicate documents, date-based version selection, and a comparison of two separate values.

**Actual assistant answer**

For an application started in December 2025, the limit was **5 attempts in 24 hours**, and the application remained available for **30 calendar days**. `[Identification retries and application expiry, effective 2025-01-01, version 2]`

**Outcome**

`wrong`

**Observation**

The response answered only the historical half of the comparison. A single retrieved chunk was insufficient.

---

## B4. Non-resident with missing address and a foreign-language document

**Question**

A non-resident personal applicant has an identity document that does not show an address and submits one supporting document written in a language other than Romanian or English. What evidence and fee may apply?

**Expected answer**

The applicant needs proof of address issued within the previous **90 days**. Depending on the case, a bank statement, utility bill, residence certificate, or public-authority document may be accepted if it shows the full name and address.

The foreign-language document may require an authorised translation. If the bank accepts it for language review without such a translation, the 2026 personal fee is **75 lei for the document**.

**Source documents**

- `02_accepted_documents_for_individuals.md`
- `08_personal_onboarding_fees_2026.md`
- `15_onboarding_for_non_residents.md`

**What makes it hard**

The answer requires a document rule, a non-resident condition, a current fee, and careful handling of the authorised-translation exception.

**Actual assistant answer**

The applicant must provide proof of address issued within the previous **90 days**. The foreign-language document may require an authorised translation; if it is accepted for review without one, the fee is **75 lei**. `[Onboarding for non-residents and multiple tax residencies, effective 2026-01-15, version 4]`

**Outcome**

`correct`

---

## B5. Separate outcomes in Online Account 2 in 1

**Question**

Can the personal component of Online Account 2 in 1 be approved while the business component remains under review, and what happens if another company representative is added?

**Expected answer**

Yes. The personal component may be approved while the business component remains under review. Rejection or delay of one component does not automatically cancel the other unless the reason affects identity, sanctions, or data integrity.

An additional company representative receives a separate invitation, completes their own verification, and is charged according to the applicable business fee schedule. The exact fee cannot be calculated until the company type is known.

**Source documents**

- `14_online_account_2_in_1_onboarding.md`
- `13_business_onboarding_fees_2026.md`

**What makes it hard**

The assistant must combine the product-outcome rule with the separate representative-verification and pricing rule, while recognising that the company type is missing.

**Actual assistant answer**

Yes. The personal account may be approved while the business component remains under review. Another company representative must complete a separate verification, and the applicable additional-representative fee is determined by the business fee schedule; an exact amount requires the company type. `[Onboarding for Online Account 2 in 1, effective 2026-02-01, version 4]`

**Outcome**

`correct`

---

# C — Must refuse

## C1. Student-loan interest rate

**Question**

What is the interest rate on the bank's student loans?

**Expected answer**

The assistant must state that student-loan products and their interest rates are not covered by the onboarding corpus. It must not invent a rate.

**Source documents**

- No supporting document exists.

**Actual assistant answer**

I cannot provide a student-loan interest rate because student loans are not covered by the available onboarding knowledge base. Please consult the bank's official product information or lending team.

**Outcome**

`refused correctly`

---

## C2. Mortgage early-repayment fee

**Question**

What early-repayment fee applies to a mortgage during a fixed-rate period?

**Expected answer**

The assistant must state that mortgage repayment fees are outside the scope of the corpus and must not infer a percentage from unrelated onboarding fees.

**Source documents**

- No supporting document exists.

**Actual assistant answer**

I cannot determine a mortgage early-repayment fee from the onboarding sources. Mortgage terms should be confirmed with the lending or mortgage department.

**Outcome**

`refused correctly`

---

## C3. Debit-card cash-withdrawal limit

**Question**

What cash-withdrawal limit applies to the debit card issued after onboarding?

**Expected answer**

The assistant must state that the corpus explains card delivery and activation but does not contain cash-withdrawal limits.

**Source documents**

- No supporting document exists.

**Actual assistant answer**

The available sources do not specify a debit-card cash-withdrawal limit. They cover card delivery and activation only. The limit must be checked in the applicable card terms or with Customer Support.

**Outcome**

`refused correctly`
