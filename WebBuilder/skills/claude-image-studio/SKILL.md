---
name: claude-image-studio
description: Generate or edit realistic project images in Claude through connected image tools, adapt licensed references to a website, and optionally render original Blender assets. Use for requested visual assets, not text-only image descriptions.
---

# Claude Image Studio

## When to use

Use when the user wants an actual photograph-like image, illustration, product scene,
reference edit or website asset. This skill is portable instructions plus optional helpers;
it does not contain an image model. Ordinary computers use a connected remote image tool,
so a dedicated GPU, Blender or a paid API key is not a default prerequisite.

## Procedure

1. Read the visual brief and the website's selected design direction. Discover the image
   tools actually available in this Claude session. Prefer an already connected, authorized
   tool that can return an image. For the no-paid-API setup, read
   [providers.md](references/providers.md) and use a suitable Hugging Face MCP Space within
   the user's available free quota. Do not assume a tool exists because these instructions
   mention it. Never describe a prompt or SVG as a generated realistic photograph.
2. If no generator is connected, give the one-time Claude/Hugging Face connection steps
   in the provider reference. Account sign-in belongs to the user. Do not create accounts,
   purchase quota, collect passwords/tokens, install multi-gigabyte local models or switch
   to a paid service automatically. A normal PC can use the remote route, but internet,
   client connector support, provider availability and quota are real prerequisites.
3. Choose the appropriate source: generate a new image for a fictional scene; edit an
   owned/licensed input when identity/product geometry must be preserved; use CC0 material
   when it genuinely fits; choose the optional Blender script for original object/3D scenes.
   Blender primitives are not a substitute for a requested realistic human photograph.
   For CC0, verify the original asset and license page, not a search-result label.
4. Build a concise image brief: subject/action, real setting, photographic medium,
   framing/negative space, light, palette, materials and constraints. A working-person
   scene should have plausible hands, tool use, protective equipment and activity. Use
   natural skin/lighting and avoid excessive retouching. Keep generated people fictional;
   do not present them as actual staff, clients or evidence of a completed job.
5. Invoke the selected image tool. Preserve exact requested product/person features in
   edits. Adapt composition, light and colors to the site; do not remove required credits
   or claim another person's work as original. Review faces/hands, perspective, objects,
   artifacts, text, suitability and license. Allow at most two focused corrections, then
   report any remaining defect. Respect the provider's returned limits/queue; do not bypass
   login, quota, CAPTCHA or model-license restrictions.
6. Save the actual returned file into the project without overwriting an original.
   Record source/provider, source asset and license URL where applicable, prompt/edit
   invariants, transformations, dimensions and SHA-256. Optional
   `python scripts/asset_studio.py record --help` can create a provenance record;
   it does not itself establish license rights or photographic realism.
7. Integrate the selected image into the web layout with useful alt text and appropriate
   dimensions. Check desktop/mobile composition and loading. Deliver the file and actual
   evidence. Use **REAL VERIFIED** only for operations performed, **STATIC CHECK** for
   metadata/code, **SIMULATED** for mocks, and **NOT VERIFIED/FAILED** when appropriate.

For optional original 3D objects, use
`blender --background --factory-startup --disable-autoexec --python scripts/render_scene.py -- --output NEW.png`.
The bundled script creates its own scene and opens no downloaded `.blend` file. Use a
bounded command timeout; the program remains an optional separately installed dependency.

## Output

Return the actual image path/link, concise prompt or reference-edit description, origin
and license record, visual review findings and test scope. If generation is unavailable,
say what is missing and provide a prepared brief labelled **NOT VERIFIED**. Do not report
the ChatGPT built-in image tool, a mock or a different provider as a verified Claude run.

## Example

"Use Claude Image Studio to create a credible illustrative electrician in a workshop
for this navy/amber website, with space for copy on the left. Use connected free tools;
save the original and review both mobile and desktop crops."
