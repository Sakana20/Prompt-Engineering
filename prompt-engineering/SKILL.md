---
name: prompt-engineering
description: Generate natural Chinese product short-video copy, avatar prompts, SmartSplit manuscripts, and Auto Oceanengine-compatible task CSVs from user-provided 商品、利益点、活动口径 or product facts. Use for 通用商品口播、淘宝闪购口播、生活化文案、数字人 Prompt、即创任务包、批量视频素材；supports configurable benefits, no-benefit tasks, and the existing 淘宝闪购默认利益点 preset.
---

# Prompt Engineering

Turn user-supplied product and campaign facts into an auditable copy-to-avatar workflow. Perform
all semantic analysis and generation directly as Codex. Do not call another LLM.

## Workflow

1. Read [campaign-contract.md](references/campaign-contract.md),
   [copywriting-rules.md](references/copywriting-rules.md), and
   [avatar-rules.md](references/avatar-rules.md).
   For CLI, configuration, batching, plugins, debug output, or output-format requests, also read
   [runtime.md](references/runtime.md) and its linked schemas.
2. Normalize the user's facts into product facts and a campaign:
   - category;
   - product name, if supplied;
   - confirmed selling points;
   - forbidden or unknown claims;
   - platform and campaign name, if supplied;
   - zero to three user-confirmed benefit points;
   - project language style, if supplied;
   - requested quantity, defaulting to one.
3. If only a category is supplied, generate a draft using generic situations and observable
   category-level properties. Do not invent material, performance, price, brand, sales, efficacy,
   promotion facts, amount, threshold, or campaign rule. State briefly that product-specific and
   campaign-specific claims require review.
4. Generate each 80–100 Chinese-character spoken copy as product-led conversational sharing.
   Keep scene setup to one or at most two sentences (about 20%), make the product, selection
   reason, and one or two confirmed details the core (about 50%). Use the remaining space for the
   configured benefit and a concrete purchase experience (about 30%); if no benefit is configured,
   use that space for purchase or usage experience. Do not expand the setup into a complete
   lifestyle story. For a batch, vary demand, product emphasis, benefit transition, and purchase
   experience.
5. Apply the campaign contract before continuing:
   - every user-confirmed `required` benefit must appear;
   - every `exact_match` benefit must preserve the original wording exactly;
   - every `no_split` benefit must be wrapped as `[[NO_SPLIT]]利益点原文[[/NO_SPLIT]]`;
   - when no benefit is supplied and no preset is selected, do not invent promotions, amounts,
     thresholds, or platform benefits.
6. Validate every copy before continuing:
   - reject banned words and only the click/purchase calls to action configured for the active
     validation config;
   - use only confirmed product facts;
   - output natural prose, not a title, list, explanation, or Markdown.
   When working from this repository, run `uv run avatar-prompts validate-copy '<copy>'` with
   matching `--benefit-point` arguments or `--preset none`, and revise any failing copy before
   generating its avatar prompt.
7. Remove `[[NO_SPLIT]]` tags before generating an avatar video prompt; they are not spoken text.
   Generate one avatar video prompt per accepted copy. Use the copy as the sole semantic basis.
   Give every prompt a different person and a different outfit. Vary face shape, visible facial
   features, hairstyle, hair color, and clothing combination while keeping the overall account
   aesthetic young, natural, clean, and approachable.
8. Before export, list an `identity_key` and `outfit_key` for every prompt and verify both are unique
   within the batch. Never use continuity wording such as “same person”, “same face”, “固定人物”,
   or “保持脸部特征一致”.
9. When the user requests an Oceanengine task package, read
   [oceanengine-contract.md](references/oceanengine-contract.md). Derive a static
   `person_prompt` from visible first-frame attributes; do not put temporal camera or lip-sync
   instructions into that image prompt.
   Strip `[[NO_SPLIT]]` tags from the CSV `script`; manuscript annotation and CSV export are
   separate operations. Never create or write a CSV merely because a copy was annotated.
   Set each CSV `notes` value to `{actual user category}+{1-based sequence}`. Never write the
   literal placeholder “品类”; for example use `西瓜+1` or `雨伞+1`.
10. Preview the copy, avatar prompt, static person prompt, product facts, and campaign facts used.
   Require explicit approval
   before any paid video submission.
11. Use the target project's own `preflight` before import. Never silently overwrite an existing
    batch file or blindly resubmit an uncertain task.

## Output Modes

- **Copy only:** return only the finished spoken copy unless the user asks for analysis.
- **Avatar prompt only:** return only the complete avatar prompt.
- **Review mode:** show copy, avatar prompt, facts used, unknowns, and risk flags.
- **Task package:** create two independent handoffs from the same accepted result:
  - one UTF-8
    `/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task_id>.smartsplit.txt`
    per task, preserving `[[NO_SPLIT]]`;
  - one batch UTF-8
    `/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv`,
    stripping `[[NO_SPLIT]]` from every `script`.
  Writing either handoff must not invoke, create, overwrite, import, or run the other consumer.
  The date directory uses local `YYYYMMDD`; both files for one task share the same task directory.
  Do not copy into the Oceanengine project or run preflight unless the user separately requests
  that workflow.

Preserve all existing CLI arguments by forwarding them unchanged through `scripts/run_cli.py`.
Validate every explicit parameter against `references/cli-parameters.schema.json` or
`references/skill-config.schema.json`. Preserve requested configuration files, batching, installed
Codex plugins, safe debug output, and all requested output formats. Never remove an existing field,
command, format, hook, or behavior while packaging or installing this skill.

Compatibility defaults:

- If the user asks for 淘宝闪购 without specifying another benefit, use preset
  `taobao-instant-commerce-default`, whose benefit is `最高12元无门槛红包`.
- If the user provides an explicit benefit, use that benefit instead of the preset.
- If the user says no benefit or no promotion, use `--preset none` semantics and generate without
  any promotional benefit.
- If the user provides a project configuration file, treat it as the complete project mouthpiece:
  use its product facts, campaign facts, benefit points, forbidden expressions, and disclosures.
  Use its language style to guide tone, viewpoint, sentence rhythm, emphasis, phrases to avoid,
  and extra style rules.
  Use the referenced validation configuration to determine banned expressions, CTA rules,
  character limits, and format rules.
  Do not combine it with the default preset or unrelated campaign arguments.

For batches, keep a one-to-one mapping among source facts, copy, avatar prompt, `task_id`, and output
row. Preserve the full avatar prompt in the audit record even though the current Oceanengine chain
only consumes the static `person_prompt` and `script`.

## Safety Boundary

- Never invent product or promotion facts.
- Never reuse the same person or the same outfit within a batch.
- Never expose cookies, tokens, browser profiles, signatures, or account identifiers.
- Never trigger `run-api-video` from a general “generate prompts” request.
- Treat import and paid generation as separate user-authorized actions.
