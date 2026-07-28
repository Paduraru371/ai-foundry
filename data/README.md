# Libra Internet Bank onboarding corpus — synthetic training data

This directory contains a **fully synthetic banking onboarding knowledge base** created for a retrieval-augmented generation exercise.

The real public name **Libra Internet Bank** and public journey labels such as personal online onboarding, business online onboarding, and a two-in-one journey are used only to make the domain coherent. All fees, thresholds, deadlines, documents, internal teams, statuses, workflows, exceptions, and version changes in these files are invented.

This corpus:

- contains no customer data;
- contains no employee data;
- contains no internal Libra Internet Bank documents;
- must not be presented as an accurate description of the bank's real policies;
- must not be used for real financial decisions or customer support.

Every knowledge document includes `synthetic: true` in its metadata header.

## Files

1. `01_personal_onboarding_overview.md` — overall personal onboarding journey.
2. `02_personal_eligibility_2025.md` — historical eligibility version.
3. `03_personal_eligibility_2026.md` — current synthetic eligibility version.
4. `04_accepted_identity_documents.md` — identity-document rules.
5. `05_video_identification_procedure.md` — long numbered procedure.
6. `06_personal_onboarding_fees_2025.md` — historical fee table.
7. `07_personal_onboarding_fees_2026.md` — current fee table.
8. `08_proof_of_address.md` — address evidence.
9. `09_business_onboarding_eligibility.md` — business eligibility.
10. `10_business_onboarding_fee_schedule.md` — business fees.
11. `11_business_onboarding_procedure.md` — long business procedure.
12. `12_two_in_one_onboarding.md` — linked personal and business journey.
13. `13_sanctions_and_pep_review.md` — compliance-review workflow.
14. `14_application_status_and_expiry.md` — statuses and versioned deadlines.
15. `15_failed_verification_and_recovery.md` — failure and retry rules.
16. `16_onboarding_complaints.md` — complaint process and absent legal details.

## Required difficult cases

| Case | Documents | Test |
|---|---|---|
| Precise number | `07_personal_onboarding_fees_2026.md` | Foreign identity-document review is exactly **1%** of initial funding, capped at **100 RON**. |
| Two documents must be combined | `03_personal_eligibility_2026.md` + `07_personal_onboarding_fees_2026.md` | Eligibility and minimum funding are separate from fees. |
| Two documents must be combined | `09_business_onboarding_eligibility.md` + `10_business_onboarding_fee_schedule.md` | Business eligibility and business costs are separate. |
| Near-duplicates that differ | `02_personal_eligibility_2025.md` vs `03_personal_eligibility_2026.md` | Similar title and content, but different limits, dates, and funding rules. |
| Near-duplicates that differ | `06_personal_onboarding_fees_2025.md` vs `07_personal_onboarding_fees_2026.md` | Fixed 2025 fee versus percentage-based 2026 fee. |
| Long procedure with steps | `05_video_identification_procedure.md`, `11_business_onboarding_procedure.md` | Chunking may split dependent numbered steps. |
| Table | `06_personal_onboarding_fees_2025.md`, `07_personal_onboarding_fees_2026.md`, `10_business_onboarding_fee_schedule.md` | Plain-text chunking may separate headings, rows, and values. |
| Contradiction across versions | `02_personal_eligibility_2025.md` vs `03_personal_eligibility_2026.md` | Account limit changes from two to three; application validity changes from 30 to 45 days. |
| Something deliberately absent | Entire corpus | Student-loan onboarding rules, interest rates, and eligibility are absent. The assistant must say the corpus does not contain the answer, without claiming whether the real bank offers such a product. |
| Something deliberately absent | `16_onboarding_complaints.md` | Real regulator, ombudsman, legal deadlines, and legal remedies are absent. |

## Suggested test questions

- What is the personal account limit for an application submitted in February 2026?
- What was the account limit in October 2025?
- Can an applicant submit only 50 RON as initial funding in 2026?
- What is the foreign document review fee for initial funding of 2,000 RON?
- What is the fee for initial funding of 15,000 RON?
- What happens after the third unsuccessful video-identification attempt?
- Can an applicant use a utility invoice as identity evidence?
- What is required and what is charged for a Start business application?
- In the two-in-one flow, can the personal account activate while the business application remains under review?
- What are Libra Internet Bank's student-loan onboarding rules?

The final question must produce an explicit knowledge-base limitation, not a fabricated answer.
