# OpenAI-Compatible Image Providers

Read this reference only when `--provider codex` is used. The provider's documented curl or HTTP example is the source of truth for protocol selection.

## Protocol Selection

| Provider contract | CLI setting | Generation | Reference edit |
| --- | --- | --- | --- |
| Responses API with `image_generation` tool | `--api-style responses` | `POST /responses` | Input images embedded in the Responses content |
| Images API | `--api-style images` | `POST /images/generations` JSON | `POST /images/edits` multipart |

The default remains `responses` for backward compatibility. Select `images` explicitly with the CLI or set `OPENAI_IMAGE_API_STYLE=images` in `.env.local`.

## Configuration

```dotenv
OPENAI_IMAGE_API_KEY=...
OPENAI_IMAGE_BASE_URL=https://provider.example/v1
OPENAI_IMAGE_API_STYLE=images
DRAW_CODEX_MODEL=gpt-image-2
```

Optional:

```dotenv
# Some providers use `image`; others document `image[]`.
OPENAI_IMAGE_FIELD=image[]
```

The script searches the current directory and its parents for `.env.local`. Process environment values take precedence. Never put a real key in a checked-in `.http` example, prompt, log, or generated metadata.

## Commands

Text-to-image through Images API:

```powershell
scripts\ask_draw.ps1 `
  --provider codex `
  --api-style images `
  --type wide `
  --size 1152x640 `
  --quality high `
  --output assets\generated\concept.png `
  --prompt "Design a full-screen AI workspace..."
```

Reference edit through Images API:

```powershell
scripts\ask_draw.ps1 `
  --provider codex `
  --api-style images `
  --mode frame-lock `
  --frame assets\reference\frame.png `
  --type wide `
  --size 1152x640 `
  --quality high `
  --output assets\generated\concept.png `
  --prompt "Keep the application frame unchanged..."
```

`--size` overrides the aspect-ratio preset sent to the provider. The provider may still return different pixel dimensions; validate the actual file.

## Images API Contract

Without references, the script sends JSON to `/images/generations`:

```json
{
  "model": "gpt-image-2",
  "prompt": "...",
  "size": "1152x640",
  "quality": "high",
  "response_format": "b64_json"
}
```

With one or more references, it sends multipart fields to `/images/edits`: `model`, the configured image field for each reference, `prompt`, `size`, `quality`, and `response_format=b64_json`.

Both paths expect the image at `data[0].b64_json`. The script validates and decodes the Base64 result before writing the output.

## Diagnostics and Stop Conditions

- Missing key before a request: confirm `.env.local` discovery and variable names; do not ask the user to paste a key into chat.
- `400`/`404`: compare endpoint, model, field name, and multipart/JSON structure with provider documentation.
- `502`/`503`/`520`/`524`: the request reached a gateway or origin but did not complete normally. Retry once after `Retry-After`, then stop.
- TLS failures that occur only in Windows PowerShell or Schannel are client/runtime issues; do not mislabel them as an API response.
- An empty output directory means generation did not complete. Do not proceed to reconstruction.

Changing size, quality, provider, model, protocol, or reference strategy requires user approval because each can change the visible result.
