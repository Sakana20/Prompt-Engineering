---
name: taobao-avatar-video
description: Generate natural Taobao Instant Commerce (淘宝闪购) Chinese short-video copy, an associated fixed-IP avatar video prompt, and an Auto Oceanengine-compatible task CSV. Use when the user provides a product category or product facts and asks for 淘宝闪购口播、生活化文案、数字人 Prompt、即创任务包、批量视频素材，or wants generated prompts written into the Auto Oceanengine project.
---

# Taobao Avatar Video

Turn user-supplied product facts into an auditable copy-to-avatar workflow. Perform all semantic
analysis and generation directly as Codex. Do not call another LLM.

## Workflow

1. Read [copywriting-rules.md](references/copywriting-rules.md) and
   [avatar-rules.md](references/avatar-rules.md).
2. Normalize the user's facts into:
   - category;
   - product name, if supplied;
   - confirmed selling points;
   - forbidden or unknown claims;
   - requested quantity, defaulting to one.
3. If only a category is supplied, generate a draft using generic situations and observable
   category-level properties. Do not invent material, performance, price, brand, sales, efficacy,
   or promotion facts. State briefly that product-specific claims require review.
4. Generate each 80–120 Chinese-character spoken copy directly from the canonical rules. For a
   batch, vary scene, opening, concern, transition, selling-point order, and ending.
5. Validate every copy before continuing:
   - preserve `淘宝闪购，最高12元无门槛红包天天享。` in meaning;
   - reject banned words and click/purchase calls to action;
   - use only confirmed product facts;
   - output natural prose, not a title, list, explanation, or Markdown.
   When working from this repository, run `uv run avatar-prompts validate-copy '<copy>'` and
   revise any failing copy before generating its avatar prompt.
6. Generate one avatar video prompt per accepted copy. Use the copy as the sole semantic basis.
   Keep the account IP stable while adapting scene, clothing, action, emotion, and product placement.
7. Treat identity honestly: text alone provides style consistency, not guaranteed facial identity.
   For strict identity, require a confirmed reference image or reusable person asset.
8. When the user requests an Oceanengine task package, read
   [oceanengine-contract.md](references/oceanengine-contract.md). Derive a static
   `person_prompt` from visible first-frame attributes; do not put temporal camera or lip-sync
   instructions into that image prompt.
   Set each CSV `notes` value to `{actual user category}+{1-based sequence}`. Never write the
   literal placeholder “品类”; for example use `西瓜+1` or `雨伞+1`.
9. Preview the copy, avatar prompt, static person prompt, and facts used. Require explicit approval
   before any paid video submission.
10. Use the target project's own `preflight` before import. Never silently overwrite an existing
    batch file or blindly resubmit an uncertain task.

## Output Modes

- **Copy only:** return only the finished spoken copy unless the user asks for analysis.
- **Avatar prompt only:** return only the complete avatar prompt.
- **Review mode:** show copy, avatar prompt, facts used, unknowns, and risk flags.
- **Task package:** create UTF-8 CSV matching the downstream contract, then run preflight.

For batches, keep a one-to-one mapping among source facts, copy, avatar prompt, `task_id`, and output
row. Preserve the full avatar prompt in the audit record even though the current Oceanengine chain
only consumes the static `person_prompt` and `script`.

## Safety Boundary

- Never invent product or promotion facts.
- Never claim strict same-face identity from text-only generation.
- Never expose cookies, tokens, browser profiles, signatures, or account identifiers.
- Never trigger `run-api-video` from a general “generate prompts” request.
- Treat import and paid generation as separate user-authorized actions.
