# Golden set v0: review sheet

All 12 cases in [`golden/v0.yaml`](golden/v0.yaml) are drafts. For each case, check the label
against its source, then set `review_status` in the YAML to `accepted` (kept as drafted) or
`changed` (you edited it). Chunk ids can be looked up in `data/corpus/ai_act_chunks.jsonl`
(rebuild with `uv run python -m ai_act_check.corpus`).

| id | label | source | flag | short description |
|---|---|---|---|---|
| prohibited-001 | prohibited | art-5-1-c | no | Social score from posts and late payments, used by landlords and gyms |
| prohibited-002 | prohibited | art-5-1-e | no | Face database built by scraping the web and CCTV |
| prohibited-003 | prohibited | art-5-1-f; art-3-pt-39 | no | Emotion scores of call-centre agents used in performance reviews |
| high_risk-001 | high_risk | anx-III-4-a; art-6-2 | no | CV ranking that auto-rejects the bottom half |
| high_risk-002 | high_risk | anx-III-5-b; art-6-2 | no | Consumer credit score for loan decisions |
| high_risk-003 | high_risk | anx-III-3-b; art-6-2 | no | AI grades vocational final exams, decides pass or fail |
| transparency-001 | transparency | art-50-1 | no | Customer-service chatbot of an energy supplier |
| transparency-002 | transparency | art-50-2 | no | Tool that generates realistic advertising images |
| minimal-001 | minimal | not covered; art-95-1 (voluntary codes) | no | Bakery sales forecast |
| minimal-002 | minimal | not covered; art-95-1 (voluntary codes) | no | Spam filter for a support inbox |
| unclear-001 | unclear | anx-III-4-a; art-6-3; rec-53 | yes | CV-to-table tool that marks missing certificates; Art. 6(3) narrow task vs filtering |
| unclear-002 | unclear | art-5-1-f; rec-18; anx-III-1-c; art-50-3 | yes | In-cab camera: fatigue (allowed) plus stress/anger detection at work |

## Open questions for the reviewer

1. **Flags on prohibited cases.** Only the two unclear cases have `should_flag: true`. Should a
   prohibited verdict always go to a human as well?
2. **Minimal cases cite nothing.** `expected_articles` is empty for both, so a perfect answer
   cites no chunk. Alternative: expect `art-95-1`.
3. **Sources are chunk ids only.** No case uses a Commission guideline yet. The guidelines on
   prohibited AI practices could back up `prohibited-003` and `unclear-002` once the
   relevant example is checked in the guideline itself.
