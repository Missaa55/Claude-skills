# AppBuilder — architecture blueprint

Status: design specification, not a functioning autonomous app builder.

## Objective

Convert a product request into a reviewed application project using a small number of specialized roles and repeatable quality gates. Keep model provider, generated code, and hosting independent.

## Tooling

Design and verification use widely known tools: shadcn/ui, Storybook, Playwright, axe-core and OWASP ZAP.

## Proposed project layout

```text
AppBuilder/
  README.md
  contracts/
    task.schema.json
    review.schema.json
  skills/
    appbuilder-orchestrator/SKILL.md
    appbuilder-design/SKILL.md
    appbuilder-quality/SKILL.md
  templates/          # future
  evaluation/         # future
```

## Handoff contract

1. **Discovery:** requirements, constraints, acceptance criteria, unknowns.
2. **Architecture:** framework, modules, data model, trust boundaries.
3. **Design:** tokens, components, accessibility, responsive behavior.
4. **Implementation:** scoped file changes, dependency constraints.
5. **Verification:** unit/integration/E2E tests, accessibility and security.
6. **Review:** evidence-backed findings, regression loop and approval.
7. **Delivery:** reproducible build, deployment plan, rollback and documentation.

A failed mandatory gate returns the task to implementation. All external side effects require user approval. No skill may claim a test was run based on a plan alone.

## Quality gates

- Build and static analysis
- Unit and integration tests
- E2E tests for critical user journeys
- Automated accessibility checks plus manual keyboard review
- Secret detection and dependency review
- Screenshot/visual review across viewport sizes
- Explicit approval before production deployment

## Non-goals for this initial design

No AI runtime, code generation engine, live preview server, automated deployment, or guarantee of application quality is implemented here.
