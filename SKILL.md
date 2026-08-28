---
name: draw-image-ui
description: >
  Generate UI design mockups, iterate on approved directions, and reconstruct screenshots into HTML/CSS or WeChat Mini Program code. Use for UI design, image-based screen generation, screenshot-to-code, landing pages, and high-fidelity reconstruction. Keep design approval separate from implementation when the user asks to review the mockup first.
---

# Draw UI

Design the screen first when visual direction is still being decided; reconstruct it only after the intended design is approved.

## 1. Align Before Generating

Confirm these facts only when they are not already clear:

1. The page and its core workflow.
2. The reference screenshot or design source, if any.
3. Which regions must remain unchanged.
4. The requested deliverable sequence: mockup only, mockup then approval then code, or direct reconstruction.

Do not repeat questions the user has already answered. If the user requests "先生成设计稿供确认，再还原", stop after presenting the validated mockup. Do not create or modify implementation files until the user explicitly approves that mockup.

Before a substantial design or reconstruction, state the locked regions, allowed changes, intended output, and anything explicitly out of scope. Do not silently add dashboards, side panels, gradients, authentication, APIs, or other product capabilities.

## 2. Choose the Reference Strategy

What appears in a reference tends to be reproduced, including unwanted content.

| Goal | Reference input |
| --- | --- |
| Free visual exploration | No reference image |
| Preserve only app chrome, navigation, or sidebar | A clean frame image with the editable content area cleared |
| Match the whole screen's visual language and composition | The full screenshot, with invariants stated in the prompt |

When only part of a screen is locked, prefer a clean frame. If creating that frame requires choosing an ambiguous crop or mask boundary, ask before altering the reference. Generate multiple related screens serially, using the approved prior screen as the next reference.

Use `--mode frame-lock` for a clean frame, `--mode replicate` for full-screen fidelity, and `--mode asset-redraw` for a standalone asset.

## 3. Generate the Mockup

Use the bundled script for image generation by default. It reads the provider URL, API key, and model from the nearest `.env.local` or the process environment and writes the decoded image to a local path. Use a runtime-provided image tool only when the user explicitly requests that tool.

```powershell
scripts\ask_draw.ps1 `
  --mode frame-lock `
  --frame C:\path\to\frame.png `
  --type wide `
  --name "screen-name" `
  --output C:\path\to\screen-name.png `
  --prompt "..."
```

The default `codex` provider means an OpenAI-compatible HTTP provider, not Codex login credentials. Without provider or protocol flags, it uses:

- `OPENAI_IMAGE_BASE_URL` + `/images/generations` for generation.
- `OPENAI_IMAGE_API_KEY` as the bearer token.
- `DRAW_CODEX_MODEL` as the model.
- `size=1152x640` for the default `wide` type, `quality=high`, and `response_format=b64_json`.

With references, the same Images API mode uses multipart `/images/edits`. The legacy Responses path remains available only through explicit `--api-style responses`; ZenMux remains available only through explicit `--provider zenmux`. For configuration and request details, read [references/openai-compatible-images.md](references/openai-compatible-images.md).

The default path requires `OPENAI_IMAGE_API_KEY` and `OPENAI_IMAGE_BASE_URL`, and reads `DRAW_CODEX_MODEL`, from the process environment or nearest `.env.local`. Never print, copy, or embed keys in generated artifacts.

### Prompt Rules

- State locked reference regions first.
- Use realistic content and examples, not placeholders.
- Use HEX colors where exact palette matters.
- Describe information and intent; avoid over-specifying pixels and grid mechanics.
- Keep the prompt under roughly 800 Chinese characters or equivalent unless the provider documents a higher safe limit.
- State important exclusions explicitly, such as no right sidebar or no gradients.

### Failure and Retry Boundary

- A transport or provider `5xx` may be retried once after the provider's `Retry-After` delay.
- If the same class of failure repeats, stop and report the endpoint, status, and whether an output file exists.
- Never change provider, model, API protocol, size, quality, reference image, or prompt semantics to make a request succeed without user approval.
- A smaller size, lower quality, or text-only generation is a visible product tradeoff; ask before applying it.
- Do not hand-roll a replacement HTTP client when the bundled script supports the confirmed protocol. Diagnose and improve the shared script instead.

After generation, inspect the actual image. Check every user exclusion and locked region before presenting it. Report the requested and returned dimensions when they differ.

## 4. Approval Gate

When approval is required, present the generated image and its path, list any known visual deviations, and wait. Do not describe a visibly noncompliant mockup as ready. A targeted edit should change only the rejected region or attribute; repeat all invariants in the edit prompt.

## 5. Reconstruct the Approved Design

Choose the target path from the repository, not from preference:

- Existing React, Vue, Next.js, Svelte, TypeScript, Electron, or Tauri app: read [references/software-reconstruction.md](references/software-reconstruction.md) and implement inside its architecture.
- Standalone HTML or no application stack: read [references/html-reconstruction.md](references/html-reconstruction.md).
- WeChat Mini Program: implement WXML/WXSS and TS/JS directly; do not generate HTML first and mechanically convert it.

Use code for layout, text, forms, tables, controls, and ordinary icons. Use assets for brand marks, complex illustrations, photographs, special textures, and visuals that would be brittle in CSS. Never use the entire mockup as a page background.

For ordinary icons, use the repository's installed icon system. If none exists, obtain the user's choice before adding a dependency or CDN. For standalone HTML, Lucide is the preferred option once approved; pin its version. Do not ship Unicode symbols, emoji, CSS-drawn imitations, or hand-authored placeholder paths as final toolbar/navigation icons.

## 6. Verify

Run the repository's checks incrementally, then its complete applicable gate. For browser verification:

1. Use an isolated preview containing only the files needed by the page; never serve a repository root that contains `.env*`, credentials, or unrelated private files.
2. Match the design viewport and capture both viewport and full-page screenshots when applicable.
3. Compare with `scripts/compare_mockup.py`, including clips for user-rejected or high-risk regions.
4. Inspect console errors and verify primary interactions.
5. Iterate on the largest visual differences first, then typography and icon alignment.

Finish with changed files, exact validation commands and results, skipped checks, known visual gaps, and the final asset/mockup paths.
