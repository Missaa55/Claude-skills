# Image tools for Claude

Checked 2026-11-22. Tool availability and free quotas can change; inspect the live tool
schema and account state before a run. A skill cannot transfer ChatGPT's internal image
tool into Claude. [Anthropic](https://support.claude.com/en/articles/9002504-can-claude-produce-images)
documents Claude's native image-generation boundary.

## Default portable route: Hugging Face MCP

The [official Hugging Face MCP server](https://huggingface.co/docs/hub/agents-mcp) exposes
selected MCP-compatible Spaces as tools in Claude. Inference runs remotely; the client PC
does not need a model, Python rendering environment or a powerful graphics card.

1. Sign in to a Hugging Face account and open [MCP settings](https://huggingface.co/settings/mcp).
2. Follow its current Claude client setup. For Claude Code, the documented command is:

   ```text
   claude mcp add --transport http hf-images "https://huggingface.co/mcp?login"
   ```

   In Claude web/Desktop, use the custom-connector flow and the same remote URL as shown
   by the current HF settings. This is an account-level action for the user to authorize.
   Do not write credentials into the skill or repository. The helper's `setup` command
   only writes a sample project configuration; it does not sign in or mutate global settings.
3. Select an appropriate image Space with an MCP badge and add it to Spaces Tools.
   For example, inspect available FLUX.1-schnell tools and verify their actual model/license.
   The [upstream FLUX.1-schnell model](https://huggingface.co/black-forest-labs/FLUX.1-schnell)
   declares Apache-2.0. A similarly named Space, another FLUX variant or a Krea/dev model
   may have different terms; do not infer commercial permission from the family name.
4. Confirm the image tool appears in Claude, then make one small test request and verify
   the returned image file. Treat successful configuration separately from successful generation.

HF also documents **Dynamic Spaces** in MCP settings: once the user enables it, Claude
can discover compatible Spaces at runtime instead of manually adding each one. This is
the preferred discovery mode when available, within the same free-quota constraint.
Keep image responses enabled if the client supports them so Claude can inspect the
result, rather than treating a returned URL as visual verification.

[HF's Spaces guide](https://huggingface.co/docs/hub/spaces-mcp-servers) describes account/token
requirements and ZeroGPU quotas. Free quota can be limited or exhausted. No always-free,
unlimited availability or equal quality to ChatGPT image generation is promised. The
selected user's preference is **no paid API**: stop on quota exhaustion or an unavailable
tool instead of silently enabling paid credits.

## Reference assets and CC0

[Poly Haven](https://polyhaven.com/license) licenses its downloadable HDRIs, textures and
models as CC0; unrelated website/example/user renders are not automatically covered.
[ambientCG](https://docs.ambientcg.com/license/) documents CC0 for its assets. For any
selected asset, retain the original asset page, license URL and file hash. CC0 copyright
status does not by itself verify every person's consent or a trademark/property release.
Do not call Pexels/Unsplash/Pixabay content CC0 without verifying its actual license.

Use a connected editing tool to change framing/background/light/grade, preserving the
requested subject. Editing does not erase the source license or make authorship original.

## Optional programs

| Program | Useful role | Dependency policy |
| --- | --- | --- |
| [Blender](https://www.blender.org/features/) | Original product/object renders, lighting, material scenes, optional animation | Optional; render script is bundled, application is separate |
| [Inkscape](https://inkscape.org/) | Editable SVG diagrams, icon systems and brand geometry | Optional; no realistic-human claim |
| [Krita](https://krita.org/en/features/) | Painting, masks, texture/art refinement | Optional; no auto-install |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | User-managed local generation workflows | Advanced optional route; model/hardware/license requirements vary |

Blender is [GPL software](https://www.blender.org/about/license/). This skill ships its
own small scene script, not Blender executables or third-party add-ons. Do not launch
untrusted scene scripts or enable Python auto-execution on downloaded `.blend` files.

## Honest verification

The repository can test helper behavior and optional Blender rendering. Authenticated
Claude + HF generation requires an actual connected user session and is **NOT VERIFIED**
until such a run produces an inspected file. A photorealistic example generated through
ChatGPT's built-in tool is evidence for that tool alone, not for Claude/HF integration.
