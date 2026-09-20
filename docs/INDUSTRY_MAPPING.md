# Industrial extensions: what is built versus what is only proposed

The 20 cases implement reusable decision workflows. They do not connect to every
industry's production systems. The mapping below makes the earlier industry examples
explicit without pretending that demonstration code is a deployed regulated workflow.

| Domain from the research discussion | Existing cases to reuse | Additional work before real use |
|---|---|---|
| Software engineering | 01–17 | Inspect repository and CI interfaces; human-reviewed evaluation |
| Cybersecurity | 06, 14, 17 | Approved alert schemas; independent analyst review; no automatic containment |
| Financial services | 02, 07, 13 | Authorized case data and domain review; no automated eligibility decisions |
| Insurance | 07, 13, 18 | Approved claims taxonomy and expert-reviewed labels; no adjudication |
| Legal workflows | 07, 10, 16 | Qualified review and document authority; not legal advice or certification |
| Customer support | 13, 18 | Actual queue adapter and service rules; no customer messages sent by this kit |
| E-commerce | 05, 07, 13 | Catalog schema and policy review; no listing changes |
| Research | 07, 19 | Licensed sources, relevance labels and evidence checks |
| Knowledge systems | 07, 20 | Actual memory API and human-approved admission policy |
| Enterprise RAG | 05, 06, 07 | Approved retrieval boundaries; do not treat triage as guaranteed injection defense |
| DevOps | 11, 14, 15 | Read-only telemetry adapter; deployment and incident authority remain external |
| Agent platforms | 01, 02, 03, 08, 12 | Inspected harness node adapters; no invented execution APIs |

These are proposed adaptation paths, not evidence that Jev is accurate or approved
for a particular high-stakes application. Start with synthetic data. Do not make
employment, credit, insurance, medical, or other consequential decisions from these
demonstration thresholds. Keep any actual external writes behind existing authorization.
