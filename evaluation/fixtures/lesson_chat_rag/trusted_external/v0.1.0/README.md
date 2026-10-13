# Trusted External Evaluation Fixture v0.1.0

Purpose:
- deterministic Step 7.2 reviewed external evidence identities only.

Review status:
- all listed sources are ACCEPTED_FOR_EVALUATION_FIXTURE.
- only the reviewed claims in reviewed-sources.json are accepted as Step 7.2 ground truth.

Runtime boundary:
- no provider selected;
- no domain allowlist configured;
- no runtime network/retrieval behavior implemented;
- Step 6.8-B remains NOT STARTED.

Provenance:
- EvaluationCases cite exact HTTPS URLs through EXTERNAL_URL EvidenceRef.
- source_id is a stable evaluation-fixture identity.
- URL/domain/title in cases must match the reviewed registry.

Negative-space safety:
- these five reviewed topics are distinct from the eight accepted NO_EVIDENCE targets.
- do not broaden reviewed claims or add unrelated external pages in this task.
