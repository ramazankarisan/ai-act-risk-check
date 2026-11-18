# Eval v0b: baseline on foundry

- Run at: 2026-11-18 22:05 UTC
- Deployment: `gpt-5-mini`
- Model id: `gpt-5-mini`
- Golden set: 12 cases, retrieval: BM25 top 8

## Metrics

| metric | value |
|---|---|
| silent miss rate (lower is better) | 0.17 |
| class accuracy (definite cases) | 0.80 |
| class accuracy (all cases) | 0.75 |
| citation precision | 0.30 |
| citation recall | 0.32 |
| flag recall | 1.00 |
| review rate | 0.25 |
| retrieval recall@8 | 0.32 |

Review rate should be close to 0.17 (share of cases that need review); read it together with flag recall.

## Cost and latency

| item | value |
|---|---|
| input tokens | 25,646 |
| output tokens | 9,750 |
| total tokens | 35,396 |
| estimated cost | $0.0259 |
| latency p50 | 5,474 ms |
| latency p95 | 9,476 ms |

## Per case

| id | expected | predicted | ok | flag should/got | expected ids | cited ids | precision | recall | silent miss | retrieval recall | latency ms | tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prohibited-001 | prohibited | prohibited | yes | no/no | art-5-1-c | art-5-1-c, rec-31 | 0.50 | 1.00 | no | 1.00 | 8,607 | 3,529 |
| prohibited-002 | prohibited | prohibited | yes | no/no | art-5-1-e | rec-43, art-5-1-e | 0.50 | 1.00 | no | 1.00 | 3,671 | 2,645 |
| prohibited-003 | prohibited | transparency | no | no/no | art-5-1-f | art-50-3, anx-III-5-d | 0.00 | 0.00 | yes | 0.00 | 7,962 | 3,553 |
| high_risk-001 | high_risk | high_risk | yes | no/no | anx-III-4-a, art-6-2 | anx-III-4-a | 1.00 | 0.50 | no | 0.50 | 3,995 | 1,835 |
| high_risk-002 | high_risk | high_risk | yes | no/no | anx-III-5-b, art-6-2 | anx-III-5-b, rec-58 | 0.50 | 0.50 | no | 0.50 | 4,343 | 2,941 |
| high_risk-003 | high_risk | high_risk | yes | no/no | anx-III-3-b, art-6-2 | rec-56, anx-III-3-b | 0.50 | 0.50 | no | 0.50 | 3,886 | 2,025 |
| transparency-001 | transparency | minimal | no | no/no | art-50-1 | rec-119, rec-134, art-3-pt-3 | 0.00 | 0.00 | yes | 0.00 | 6,938 | 2,897 |
| transparency-002 | transparency | transparency | yes | no/yes | art-50-2 | art-50-4, rec-99, anx-XIII-d, rec-105 | 0.00 | 0.00 | no | 0.00 | 9,375 | 2,973 |
| minimal-001 | minimal | minimal | yes | no/no | art-95-1 | rec-28, rec-72, rec-20, anx-IV-2-c, art-27-1 | 0.00 | 0.00 | no | 0.00 | 6,446 | 3,378 |
| minimal-002 | minimal | minimal | yes | no/no | art-95-1 | rec-97, art-4, art-3-pt-3 | 0.33 | 0.00 | no | 0.00 | 5,110 | 2,959 |
| unclear-001 | unclear | unclear | yes | yes/yes | anx-III-4-a, art-6-3, rec-53 | rec-174, art-44-2, anx-VII-4-6, anx-VII-4-7 | 0.00 | 0.00 | no | 0.00 | 5,474 | 2,422 |
| unclear-002 | unclear | high_risk | no | yes/yes | art-5-1-f, rec-18, anx-III-1-c | rec-18, rec-47, rec-52, rec-72 | 0.25 | 0.33 | no | 0.33 | 9,476 | 4,239 |

## Reasoning

**prohibited-001** (prohibited): The Veltrona system creates a social score of natural persons based on social behaviour and third‑party data and landlords/gyms use low scores to refuse contracts, which fits the prohibited practice described in art-5-1-c. Recital rec-31 explains that such social scoring by public or private actors that leads to detrimental or exclusionary treatment should be prohibited.

**prohibited-002** (prohibited): Orbisane Data’s system creates and expands a facial recognition database by untargeted scraping of face images from public websites and leaked CCTV footage, which is exactly the practice described as prohibited in art-5-1-e. Recital rec-43 further explains this practice should be prohibited because it contributes to mass surveillance and risks gross violations of fundamental rights.

**prohibited-003** (transparency): The system described is an emotion recognition application (inferring frustration/boredom/anger), which triggers the transparency obligations in art-50-3 requiring deployers to inform natural persons exposed to the system and to process personal data in line with applicable data-protection law. The Annex III excerpt (anx-III-5-d) shows the kinds of systems classified as high-risk (e.g., emergency-call triage), and does not list workplace emotion monitoring, so the appropriate classification from the provided context is a transparency duty rather than a high-risk or prohibited practice.

**high_risk-001** (high_risk): The AI reads, ranks and automatically rejects candidates in the recruitment/selection process, which falls squarely within Annex III point 4(a). That provision explicitly lists AI systems intended to be used to analyse and filter job applications and evaluate candidates as high-risk, so this use case is classified as high-risk.

**high_risk-002** (high_risk): The use case (AI to predict default risk and set credit scores for consumer loans) matches exactly the category in anx-III-5-b, which lists AI systems intended to evaluate creditworthiness or establish credit scores as high-risk. Recital 58 further explains that such systems determine access to financial resources and essential services and may cause discrimination or exclusion, supporting the high-risk classification.

**high_risk-003** (high_risk): The system automatically grades final exams and its grade decides pass/fail, which is an evaluation of learning outcomes; rec-56 explicitly states AI systems used to evaluate learning outcomes that materially affect a person’s education or livelihood should be classified as high-risk. Annex III point 3(b) (anx-III-3-b) specifically lists AI systems intended to evaluate learning outcomes as high-risk, matching this use case.

**transparency-001** (minimal): The system is a consumer-facing online chatbot for routine queries; rec-119 explicitly discusses online chatbots as intermediary services. The specific transparency labelling duty in rec-134 is focused on deep fakes and AI-generated content published on matters of public interest, which does not describe routine customer support. Art-3-pt-3 shows Brimworth would be a 'provider' subject to general obligations, but the use case does not match prohibited practices or the typical high-risk areas in Annex III, so it falls under minimal risk.

**transparency-002** (transparency): The system is a general-purpose text-to-image generative model (rec-99; anx-XIII-d), and Article 50(4) requires deployers of AI that generate or manipulate image content constituting a deep fake to disclose that the content is artificially generated (art-50-4). Because Pictavo’s tool produces realistic images used in public advertising, a transparency duty is likely triggered; however it is unclear from the provided excerpts whether these product images qualify as ‘deep fakes’ (the provision targets generated/manipulated image content constituting deep fakes) and there are additional legal risks such as copyright of training data (rec-105), so human review is advised.

**minimal-001** (minimal): The bakery's use case is a routine commercial forecasting tool to plan baking and does not resemble the manipulative or abusive practices the Regulation says should be prohibited (rec-28). The more onerous transparency, documentation and fundamental-rights assessment duties described in the context apply to high-risk AI systems and prescribe specific obligations for those cases (rec-72, anx-IV-2-c, art-27-1). This forecasting use is a typical deployer scenario where AI literacy and voluntary measures are appropriate rather than the mandatory high-risk regime (rec-20). Therefore it falls outside the prohibited and high-risk categories and is classified as minimal risk.

**minimal-002** (minimal): The use case is an internal email-filtering tool to separate spam/phishing from customer emails and does not match any prohibited practice or the high-risk categories indicated in the provided context. Recital 97 states obligations for models do not apply when an own model is used for purely internal processes and the rights of natural persons are not affected, and Article 3(3) defines the roles of providers/deployers while Article 4 requires AI literacy measures for staff. Taken together, this indicates the scenario falls under minimal risk (general obligations/voluntary codes) rather than prohibited, high-risk, or transparency-specific duties.

**unclear-001** (unclear): The provided context does not state whether CV-parsing / candidate screening systems are listed in the Annexes as high-risk; rec-174 shows the Commission reviews and may amend the list of high-risk AI systems. Articles and annex excerpts (art-44-2, anx-VII-4-6, anx-VII-4-7) describe conformity and certification procedures that would apply if the system were in an Annex, but do not indicate that this specific recruiting use is included. Therefore a human decision is needed to determine if this recruiting tool falls under an Annex (high-risk) or not.

**unclear-002** (high_risk): The system includes a driver drowsiness/fatigue detector intended to prevent accidents, and rec-18 explicitly excludes such fatigue-detection uses from the definition of 'emotion recognition.' Rec-47 and rec-52 indicate that AI systems that operate as safety components of products or otherwise pose high risks to health and safety should be classified as high-risk. Rec-72 further supports that such high-risk systems require specific transparency and documentation obligations. However, the presence of an emotion-recognition function (flagging ‘stressed or angry’) raises additional fundamental-rights and privacy concerns and could be regulated differently, so human review is advised.
