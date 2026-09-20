# Primary-source register

Verified on **2026-09-20**. Public documentation can change. Recheck the exact contract
before changing this kit's pins. No private early-access terms were available.

| Source | URL | Used for |
|---|---|---|
| TypeSafe API | https://docs.typesafe.ai/api | Fixed endpoint, typed questions and answers, usage, errors |
| TypeSafe models | https://docs.typesafe.ai/models | Version pin, text-only input, alias semantics |
| TypeSafe confidence | https://docs.typesafe.ai/confidence | Confidence versus probability and uncertainty handling |
| TypeSafe skill | https://docs.typesafe.ai/agent-skill | Official skill installation and role |
| Upstream skill | https://github.com/typesafe-ai/skills | Source review and attribution; not vendored |
| Jev limitations | https://docs.typesafe.ai/model-jaggedness/jev-1.13 | Boundaries of semantic judgment |
| System One architecture | https://docs.typesafe.ai/concepts/how-to-build-with-system-one | Keep side effects and control flow in code |
| Skill selection cookbook | https://docs.typesafe.ai/cookbooks/skill_suggestion | Routing pattern inspiration |
| RAG passage cookbook | https://docs.typesafe.ai/cookbooks/classifying_rag_passages | Passage triage pattern inspiration |
| Codex MCP | https://developers.openai.com/codex/mcp | Project MCP, stdio process and environment forwarding |
| Codex skills | https://developers.openai.com/codex/skills | Project skill discovery and SKILL.md |
| MCP stdio | https://modelcontextprotocol.io/specification/2025-11-25/basic/transports | Newline JSON-RPC, protocol-only stdout |
| Playwright screenshots | https://playwright.dev/python/docs/screenshots | Real page screenshots |
| Playwright video | https://playwright.dev/python/docs/videos | Browser recording lifecycle |
| Playwright releases | https://playwright.dev/python/docs/release-notes | Target dependency pin reviewed at 1.63 |
| Public customer agreement | https://typesafe.ai/legal/mca | Correct earlier unsubstantiated benchmark restriction |

## 2026 update and corrections

Jev's current documented model is `jev-1.13.0`. Use a versioned pin rather than assuming
an alias will remain stable. The adapter implements a deliberately narrower subset of
the documented API: text/JSON state, string question instructions, simple rubrics.
Noul returns its `noul` value without a separate confidence field. Score can be fractional.
Question IDs are mapping keys, not semantic instructions visible to the model.

The current documented input is text only; images, recordings and reels are output
artifacts for evidence, not direct Jev input. Jev is hosted, not installed as local weights.
Codex skills teach workflows; MCP exposes callable tools. Neither alone creates a
mandatory interceptor around every native agent action. Model nicknames are not treated
as installable provider identifiers; the existing user-selected coding model is preserved.

The public agreement reviewed above does not support the earlier blanket claim that
benchmarks cannot be published. Review separate early-access obligations before sharing.
