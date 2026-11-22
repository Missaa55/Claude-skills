# WebBuilder

A coordinated collection of website-specific skills for research, design, implementation, quality assurance and publishing. This is **not** a running visual editor or an AI website generator.

## Cooperation model

```text
Website brief
  -> research / sitemap
  -> design system / layout / content
  -> implementation (Applications/web-frontend)
  -> accessibility + performance + visual QA + security
  -> publishing (approval required)
```

If a website needs authentication, APIs or databases, delegate to `Applications/`. For general review and testing use `Universal/`. For Minecraft server websites, involve `Minecraft/`. AppBuilder can coordinate broader application scope.

## Skills

- `webbuilder-orchestrator` — Route website tasks across discovery, design, implementation and quality gates.
- `webbuilder-research` — Analyze a website brief, audience, sitemap and content structure.
- `webbuilder-design-system` — Build coherent visual language and reusable responsive website components.
- `webbuilder-layout` — Implement responsive page structure and interaction states.
- `webbuilder-content-seo` — Plan website copy, metadata, structured content and search discoverability.
- `webbuilder-accessibility` — Audit WCAG-relevant interactions and semantics for websites.
- `webbuilder-performance` — Measure and improve website load and runtime performance.
- `webbuilder-visual-qa` — Detect unintended visual changes across viewport sizes and UI states.
- `webbuilder-security` — Review web-specific input, content, dependency and deployment risks.
- `webbuilder-publishing` — Prepare reproducible static or dynamic website releases.
- `webbuilder-cms` — Plan content models and editorial workflow for a website.
- `webbuilder-integration` — Coordinate WebBuilder with AppBuilder, Applications, Universal and Minecraft skills.

## Tooling

Implementation and checks use widely known tools: Next.js, Astro, shadcn/ui, Storybook, Playwright, axe-core and Lighthouse. Page implementation stays in `Applications/web-frontend`.

## Quality gates

- Semantic structure, responsive behavior and keyboard access
- Working navigation, forms, links and error states
- Repeatable build and browser tests
- Performance and accessibility reports with known limitations
- Security and third-party dependency review
- Screenshot review at representative viewports
- User approval before deployment

## Verification

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
python3 framework/route.py "Build a responsive website with SEO"
```

Routing is advisory; no agents or browsers are launched by these commands.
