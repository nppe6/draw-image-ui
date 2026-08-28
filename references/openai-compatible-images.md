# OpenAI-Compatible Image Providers

Read this reference for the default image generation path. The contract in `.http/index.http` is the source of truth.

## Protocol Selection

| Provider contract | CLI setting | Generation | Reference edit |
| --- | --- | --- | --- |
| Images API | Default, no flag required | `POST /images/generations` JSON | `POST /images/edits` multipart |
| Responses API with `image_generation` tool | Explicit `--api-style responses` | `POST /responses` | Input images embedded in the Responses content |

Do not select a protocol during ordinary use. The script defaults to the Images API contract. Use `--api-style responses` only when the user explicitly requests the legacy Responses path.

## Configuration

```dotenv
OPENAI_IMAGE_API_KEY=...
OPENAI_IMAGE_BASE_URL=https://provider.example/v1
DRAW_CODEX_MODEL=gpt-image-2
```

Optional:

```dotenv
# Only needed for reference edits when the provider documents a different multipart field.
OPENAI_IMAGE_FIELD=image[]
```

The script searches the current directory and its parents for `.env.local`. Process environment values take precedence. Never put a real key in a checked-in `.http` example, prompt, log, or generated metadata.

## Commands

Text-to-image through Images API:

```powershell
scripts\ask_draw.ps1 `
  --type wide `
  --output assets\generated\concept.png `
  --prompt "Design a full-screen AI workspace..."
```

Reference edit through Images API:

```powershell
scripts\ask_draw.ps1 `
  --mode frame-lock `
  --frame assets\reference\frame.png `
  --type wide `
  --output assets\generated\concept.png `
  --prompt "Keep the application frame unchanged..."
```

The default `wide` request sends `size=1152x640` and `quality=high`. `--size` and `--quality` explicitly override those values. The provider may still return different pixel dimensions; validate the actual file.

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
