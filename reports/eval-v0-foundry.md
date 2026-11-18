# Eval v0: baseline on foundry

- Run at: 2026-11-18 21:46 UTC
- Deployment: `gpt-5-mini`
- Model id: `gpt-5-mini`
- Golden set: 12 cases, retrieval: BM25 top 8

## Metrics

| metric | value |
|---|---|
| class accuracy (definite cases) | 0.70 |
| class accuracy (all cases) | 0.75 |
| citation precision | 0.32 |
| citation recall | 0.32 |
| flag recall | 1.00 |
| review rate | 0.25 |

Review rate should be close to 0.17 (share of cases that need review); read it together with flag recall.

## Cost and latency

| item | value |
|---|---|
| input tokens | 25,646 |
| output tokens | 8,599 |
| total tokens | 34,245 |
| estimated cost | $0.0236 |
| latency p50 | 5,531 ms |
| latency p95 | 8,031 ms |

## Per case

| id | expected | predicted | ok | flag should/got | expected ids | cited ids | precision | recall | latency ms | tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| prohibited-001 | prohibited | prohibited | yes | no/no | art-5-1-c | art-5-1-c, rec-31 | 0.50 | 1.00 | 6,657 | 3,231 |
| prohibited-002 | prohibited | prohibited | yes | no/no | art-5-1-e | rec-43, art-5-1-e | 0.50 | 1.00 | 3,881 | 2,660 |
| prohibited-003 | prohibited | transparency | no | no/no | art-5-1-f | art-50-3 | 0.00 | 0.00 | 5,531 | 3,092 |
| high_risk-001 | high_risk | high_risk | yes | no/no | anx-III-4-a, art-6-2 | anx-III-4-a | 1.00 | 0.50 | 3,509 | 1,802 |
| high_risk-002 | high_risk | high_risk | yes | no/no | anx-III-5-b, art-6-2 | anx-III-5-b, rec-58 | 0.50 | 0.50 | 5,361 | 3,137 |
| high_risk-003 | high_risk | high_risk | yes | no/no | anx-III-3-b, art-6-2 | rec-56, anx-III-3-b | 0.50 | 0.50 | 3,918 | 1,929 |
| transparency-001 | transparency | minimal | no | no/no | art-50-1 | rec-119, rec-134, art-3-pt-3, art-62-3 | 0.00 | 0.00 | 7,285 | 2,961 |
| transparency-002 | transparency | unclear | no | no/yes | art-50-2 | rec-99, art-50-4 | 0.00 | 0.00 | 8,031 | 2,886 |
| minimal-001 | minimal | minimal | yes | no/no | art-95-1 | rec-20, rec-28, art-27-1 | 0.00 | 0.00 | 5,030 | 3,172 |
| minimal-002 | minimal | minimal | yes | no/no | art-95-1 | rec-97, art-4 | 0.50 | 0.00 | 5,809 | 3,053 |
| unclear-001 | unclear | unclear | yes | yes/yes | anx-III-4-a, art-6-3, rec-53 | rec-174, art-23-5, anx-VII-4-6 | 0.00 | 0.00 | 5,928 | 2,468 |
| unclear-002 | unclear | unclear | yes | yes/yes | art-5-1-f, rec-18, anx-III-1-c | rec-18, rec-29, rec-52 | 0.33 | 0.33 | 7,534 | 3,854 |

## Reasoning

**prohibited-001** (prohibited): The system creates a social score of natural persons based on their social behaviour (social media posts, payment history, neighbourhood complaints) and landlords/gyms use low scores to refuse contracts, which matches the prohibited practice in art-5-1-c (evaluation/classification over time with social scores causing detrimental or unfavourable treatment). Rec-31 explains such social scoring by private actors leads to discriminatory outcomes and exclusion, supporting the prohibition of this use.

**prohibited-002** (prohibited): Orbisane’s practice of untargeted scraping of face photos from public websites and leaked CCTV to create and expand a facial recognition database directly matches the prohibition described in art-5-1-e. Recital rec-43 explicitly explains that creating or expanding facial recognition databases through untargeted scraping should be prohibited because it facilitates mass surveillance and rights violations, which fits this use case.

**prohibited-003** (transparency): The described system is an emotion recognition system applied to workers (inferring frustration, boredom, anger) and used by deployers in performance reviews. Article 50(3) explicitly imposes transparency obligations on deployers of emotion recognition systems (informing exposed natural persons and processing personal data in accordance with EU data-protection law), indicating this use falls under the transparency category rather than being prohibited or listed as high-risk in the provided context.

**high_risk-001** (high_risk): The AI is explicitly used for recruitment/selection by analysing, filtering and evaluating candidates and automatically rejecting half of applicants, which matches the Annex III listing for employment, workers’ management and access to self-employment (anx-III-4-a). Therefore this use falls squarely within the high-risk category defined in that Annex and is subject to the corresponding requirements.

**high_risk-002** (high_risk): Annex III explicitly lists AI systems intended to evaluate the creditworthiness of natural persons or establish their credit score as high-risk (anx-III-5-b). Recital 58 reinforces that AI systems used to evaluate credit scores/creditworthiness should be classified as high-risk because they determine access to financial resources and can produce discriminatory or exclusionary impacts.

**high_risk-003** (high_risk): The AI grades final exams and its output decides whether a student passes the module, which is an evaluation of learning outcomes used to determine educational progression. rec-56 states AI systems used to evaluate learning outcomes in education should be classified as high-risk, and anx-III-3-b explicitly lists AI systems intended to evaluate learning outcomes as high-risk under Article 6(2).

**transparency-001** (minimal): The chatbot is a customer-service tool provided by an electricity supplier and falls within the general scope of the Regulation (rec-119) and the definition of a provider (art-3-pt-3). The provided context only sets out specific transparency duties for deep fakes or AI-generated text on matters of public interest (rec-134), which does not describe routine tariff/metering/customer-service interactions. The other excerpts (art-62-3) point to supportive measures for providers rather than classification as high-risk or prohibited, so this use case is not identified in the context as prohibited, high-risk, or subject to special transparency duties and is therefore minimal risk.

**transparency-002** (unclear): Large generative models can produce realistic images (rec-99). Article 50(4) imposes a transparency duty on deployers that generate or manipulate image content constituting a deep fake, requiring disclosure (art-50-4). Whether Pictavo’s product photos/ads trigger that duty depends on if the outputs qualify as "deep fakes" or otherwise fall under the disclosure rules, which is not specified in the use case, so a human review/decision is needed.

**minimal-001** (minimal): The bakery’s demand-forecasting model is a routine business decision‑support tool for planning production and does not involve manipulative or abusive social‑control practices that Article 5 seeks to prohibit (rec-28). It also does not fall into the kinds of high‑risk uses that trigger mandatory fundamental‑rights impact assessments and the other specified high‑risk obligations (art-27-1). Guidance in the context recognizes that many AI uses are addressed by AI literacy, voluntary codes and ordinary deployer obligations rather than prohibition or high‑risk regimes (rec-20).

**minimal-002** (minimal): The use case is an internal spam/phishing filter for a webshop’s customer-service inbox, which is a routine operational tool rather than a prohibited practice or one of the high-risk application areas listed in the Regulation. Recital 97 explains that obligations for general-purpose models apply when models are placed on the market and that internal uses which do not affect the rights of natural persons may be out of scope; this filtering is an internal operational aid. Article 4 imposes duties like AI literacy on providers and deployers but does not classify such an internal email-filtering tool as high-risk or subject to the transparency rules in the cited context.

**unclear-001** (unclear): The context mentions the existence and periodic review of a list of high-risk AI systems (rec-174) and regulatory obligations that apply to ‘high-risk’ systems (art-23-5), as well as detailed conformity/certification procedures for systems subject to those rules (anx-VII-4-6). The provided chunks do not include Annex III or any explicit statement that recruitment/selection tools are (or are not) high-risk, so it is not possible from the supplied context alone to determine whether this CV-processing and flagging tool falls under the high-risk category or instead remains subject only to transparency/minimal obligations. A human review against the Annex III list and the full Regulation is needed.

**unclear-002** (unclear): rec-18 distinguishes fatigue/drowsiness detection (explicitly excluded from the definition of 'emotion recognition') from systems that identify emotions such as anger or stress, so the drowsiness function could be non-emotion-sensing while the 'stressed or angry' flagging is an emotion-recognition feature. rec-29 prohibits manipulative or exploitative AI that materially distorts behaviour or exploits vulnerabilities, which could be relevant if emotion inference is used in ways that affect drivers' autonomy or causes harm. rec-52 indicates that stand-alone systems may be classified as high-risk depending on intended purpose and the severity/probability of harm. Given these tensions (safety justification for drowsiness detection versus the presence of emotion inference and possible rights impacts), a human reviewer should decide whether the emotion-detection component renders the overall system prohibited, high-risk, subject to transparency duties, or otherwise regulated.
