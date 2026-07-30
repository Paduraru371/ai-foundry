# Banking onboarding corpus

This directory contains a focused knowledge corpus for evaluating retrieval-augmented generation in personal and business onboarding. Each knowledge document contains YAML front matter that can be converted into searchable metadata.

## Scope

- personal account onboarding;
- business account onboarding;
- remote identity verification;
- customer due diligence and beneficial ownership;
- fees, timelines, activation, rejection, and complaints;
- active and superseded versions dated 2025 and 2026.

`README.md` is an inventory document and should be excluded from the production knowledge index.

## Difficult cases included

| Required case | Documents | Test design |
|---|---|---|
| Precise number | `05_manual_review_and_processing_times.md`, `08_personal_onboarding_fees_2026.md`, `19_identification_retries_2026.md` | 2 working days, 75 lei per document, 3 attempts, and 15 days |
| Two documents must be combined | `09_online_business_account_eligibility.md` and `13_business_onboarding_fees_2026.md` | Eligibility and pricing are stored separately |
| Near-duplicates with different answers | `07_personal_onboarding_fees_2025.md` and `08_personal_onboarding_fees_2026.md` | Similar fee schedules with different dates and amounts |
| Long procedure | `04_complete_personal_onboarding_procedure.md` and `12_complete_business_onboarding_procedure.md` | Procedures with 17 and 20 ordered steps |
| Table | `07_personal_onboarding_fees_2025.md`, `08_personal_onboarding_fees_2026.md`, and `13_business_onboarding_fees_2026.md` | Markdown tables with fees by service or applicant type |
| Contradiction across versions | `18_identification_retries_2025.md` and `19_identification_retries_2026.md` | The limit changes from 5 to 3 attempts and the validity period from 30 to 15 days |
| Deliberately absent information | No document covers student loans, mortgages, or card cash-withdrawal limits | The assistant must decline to invent an answer |

## Suggested validation prompts

1. How many video-identification attempts are permitted for an application started in February 2026?
2. What limit applied in December 2025?
3. What is the fee for reviewing two foreign-language documents for a personal customer in 2026?
4. Can a company with three ownership levels open an account, and what opening fee applies?
5. What are all the steps after video identification in business onboarding?
6. Can the personal component be approved while the business component of Online Account 2 in 1 remains under review?
7. What evidence may be required for an indirect beneficial owner?
8. What is the interest rate on student loans?

For question 8, the correct behaviour is to state that the information is not available in the corpus rather than estimate it.
