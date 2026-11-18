# Golden set v0: review sheet

Review of the 12 cases in [`golden/v0.yaml`](golden/v0.yaml), done by the maintainer on
2026-11-18. Chunk ids can be looked up in `data/corpus/ai_act_chunks.jsonl` (rebuild with
`uv run python -m ai_act_check.corpus`).

| id | label | source | acceptable | flag | status | short description |
|---|---|---|---|---|---|---|
| prohibited-001 | prohibited | art-5-1-c | - | no | accepted | Social score from posts and late payments, used by landlords and gyms |
| prohibited-002 | prohibited | art-5-1-e | - | no | accepted | Face database built by scraping the web and CCTV |
| prohibited-003 | prohibited | art-5-1-f; art-3-pt-39 | art-3-pt-39 | no | accepted | Emotion scores of call-centre agents used in performance reviews |
| high_risk-001 | high_risk | anx-III-4-a; art-6-2 | - | no | accepted | CV ranking that auto-rejects the bottom half |
| high_risk-002 | high_risk | anx-III-5-b; art-6-2 | - | no | accepted | Consumer credit score for loan decisions |
| high_risk-003 | high_risk | anx-III-3-b; art-6-2 | - | no | accepted | AI grades vocational final exams, decides pass or fail |
| transparency-001 | transparency | art-50-1 | - | no | accepted | Customer-service chatbot of an energy supplier |
| transparency-002 | transparency | art-50-2 | - | no | accepted | Tool that generates realistic advertising images |
| minimal-001 | minimal | not covered; art-95-1 (voluntary codes) | art-4 | no | changed | Bakery sales forecast |
| minimal-002 | minimal | not covered; art-95-1 (voluntary codes) | art-4 | no | changed | Spam filter for a support inbox |
| unclear-001 | unclear | anx-III-4-a; art-6-3; rec-53 | - | yes | accepted | CV-to-table tool that marks missing certificates; Art. 6(3) narrow task vs filtering |
| unclear-002 | unclear | art-5-1-f; rec-18; anx-III-1-c; art-50-3 | art-50-3 | yes | accepted | In-cab camera: fatigue (allowed) plus stress/anger detection at work |

## Decisions

1. **Flags on prohibited cases: no.** Only unclear cases have `should_flag: true`, so
   `flag_recall` measures whether borderline cases reach a human.
2. **Minimal cases cite `art-95-1`.** `expected_articles` changed from empty to `[art-95-1]`
   (voluntary codes of conduct for non-high-risk systems), so those two cases are `changed`.
3. **Commission guidelines as sources: later.** Add them once the relevant example has been
   checked in the guideline text, for example the guidelines on prohibited AI practices for
   `prohibited-003` and `unclear-002`.
4. **Expected vs acceptable citations.** `expected_articles` must be cited (recall counts
   them). `acceptable_articles` are correct but not required: citing them does not lower
   precision. Added from each case's `source` (`art-3-pt-39`, `art-50-3`) and `art-4`
   (AI literacy) on both minimal cases. Statuses unchanged.
5. **Flag means uncertain, not severe.** Written into the `GoldenCase` docstring and the
   `v0.yaml` header. `flag_recall` is reported together with `review_rate`, so flagging
   every case is not free.
