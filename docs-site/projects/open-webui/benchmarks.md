---
id: benchmarks
title: Benchmarks
sidebar_position: 9
---

# Benchmarks

A consolidated, fully-sourced comparison of the eight workspace models. **Every number is cited.** Read the caveats — they matter.

## Reading this page

- Scores come from vendor model cards, technical reports, and reputable secondary write-ups (linked per cell on each model page).
- These models are recent (Jan–Jun 2026). Where a vendor publishes figures only for a specific **variant** (e.g. DeepSeek "-Max") or a **different size** than the one deployed locally (e.g. Qwen3-VL), it is flagged. Do not treat a flagged number as the local endpoint's guaranteed score.
- Blank cells mean **no verifiable published benchmark** for that model on that axis — not zero, and not estimated.

## Text / reasoning models

| Model | SWE-bench Verified | MMLU-Pro | GPQA(-Diamond) | LiveCodeBench | Notes |
|-------|:---:|:---:|:---:|:---:|-------|
| DeepSeek V4 Flash | ~79% | 86.2%¹ | — | 91.6 | ¹ "-Max" variant |
| DeepSeek V4 Pro | 80.6%¹ | 87.5%¹ | 90.1%¹ | 93.5 | ¹ "-Max" variant |
| Gemma 4 12B | — | ~77.2%² | 78.8%² | — | ² secondary sources; Google published no full table |
| GLM-4.7 Flash | 59.2% | — | competitive | — | τ²-Bench 79.5 (tool use) |
| Devstral Small 2 24B | 68.0% | — | — | — | code specialist |
| Qwen3 14B (base) | — | 61.03 | 39.90 | — | MMLU 81.05 |
| Qwen3 14B (thinking) | — | — | 64.0 (Diamond) | — | MMLU-Redux 89.5 |

## Vision models

| Model | MMMU | DocVQA | MMBench | Other | Notes |
|-------|:---:|:---:|:---:|------|-------|
| Qwen3-VL | — | — | 89.3–89.5³ | Design2Code 92.0; RealWorldQA 79.2 | ³ figures for 32B/235B sizes — local tag size unverified |
| Llama 3.2 Vision (11B) | 50.7% | 88.4% | — | MathVista 51.5; VQAv2 75.2 | 11B variant |

## Headline takeaways (with the caveats applied)

- **Best published coding scores:** DeepSeek V4 Pro (SWE-bench 80.6%, LiveCodeBench 93.5) — but it's the fee tier and figures are the "-Max" variant.
- **Best local coder:** Devstral Small 2 24B (SWE-bench 68.0%) — strongest free/local SWE result in the stack.
- **Best local agent:** GLM-4.7 Flash (τ²-Bench 79.5) — built for tool calling.
- **Best local generalist:** Qwen3 14B with thinking (MMLU-Redux 89.5, GPQA-Diamond 64.0) or Gemma 4 12B (GPQA Diamond ~78.8%, with the secondary-source caveat).
- **Vision:** Qwen3-VL leads on MMBench/Design2Code (large-size figures); Llama 3.2 Vision is strong on DocVQA (88.4%).

## Per-model sources

Full citations live on each model page: [DeepSeek V4 Flash](./models/deepseek-v4-flash#sources), [DeepSeek V4 Pro](./models/deepseek-v4-pro#sources), [Gemma 4 12B](./models/gemma4-12b#sources), [GLM-4.7 Flash](./models/glm-4.7-flash#sources), [Devstral Small 2](./models/devstral-small-2#sources), [Qwen3 14B](./models/qwen3-14b#sources), [Qwen3-VL](./models/qwen3-vl#sources), [Llama 3.2 Vision](./models/llama-vision#sources).
