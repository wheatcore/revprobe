# Project landscape and positioning

Reviewed on 2026-10-19. This is a targeted search, not proof of global novelty.

| Project | Published focus | RevProbe's specific focus |
| --- | --- | --- |
| [RAGProbe](https://github.com/AntonGlenbovitch/ragprobe) | Store and evaluate RAG datasets and model configurations | Derive probes from the changed clauses of two document revisions |
| [ragcitecheck](https://github.com/ppon1086/ragcitecheck) | Measure citation and evidence stability across runs | Check whether a changed fact or source revision remains stale |
| [temporal-rag](https://github.com/Emmimal/temporal-rag) | Filter and rerank retrieved documents using validity and age | Test a deployed assistant from outside its retrieval implementation |

RevProbe is intentionally small: section-aware text diff, optional LLM-written questions, version hashes, offline/live answers, and explicit inconclusive verdicts. It is suitable as an inspectable portfolio project and a starting point for real adapters. It does not claim to be the first tool in this category.
