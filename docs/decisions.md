# ResearchHub decisions

## ADR-001: Keep Phase 0 intentionally small

**Question:** Why build a static landing page before accounts and projects?

**Decision:** The landing page gives us a real Next.js surface to practise components, CSS, interactions, and Git without prematurely designing the authenticated product. The “Get started” button is deliberately a local interaction for now; Phase 1 will replace it with authentication.

**Next experiment:** Start the frontend, change a visible sentence, and refresh the browser. Notice that source-code changes persist because they are saved as files, unlike temporary UI state that we will introduce in Phase 1.
