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
   For production-volume copy based on the supplied human-written samples, also read
   [volume-copy-source-blocks.md](references/volume-copy-source-blocks.md) and
   [source-block-contracts.md](references/source-block-contracts.md). Classify the product and its
   consumption need before selecting a block. For a batch, assign exactly `floor(N/2)` rows to
   `human_rewrite`. For the remaining rows, use compatible `source_fill` blocks when available and
   otherwise use `natural_generate`; ten rows therefore always contain five rewrites. In
   `source_fill`, select one whole
   source block, fill only its bracketed slots, preserve its wording and order, and flatten line
   breaks only at final output. In `human_rewrite`, select one concrete source block, retain at
   least two recognizable words or short phrases from it, and rewrite with its abrupt, repetitive,
   conversational logic. Do not first summarize the style or turn it into polished setup-product-
   experience prose. Record `copy_mode` in every new batch task, and record `source_block_id` only
   for `source_fill` and `human_rewrite`. For every
   `source_fill`, also record each actual bracket substitution in source order as
   `source_slot_values`; campaign, platform, delivery, benefit, and CTA wording must never enter
   those values. Sample
   benefits, prices, promotions, CTAs, and unconfirmed product claims are never reusable facts.
   Before selecting a block, use the current local month: March–May is
   spring, June–August summer, September–November autumn, and December–February winter. In
   `source_fill`, reject blocks from another season. In `human_rewrite`, a block from another
   season may be used only as a language-and-structure reference: rebuild every seasonal setting
   and temperature expression for the current season, and retain at least two non-seasonal source
   phrases as anchors. Do not mechanically replace one season word with another. The final copy
   must contain no conflicting seasonal wording and must pass the same validator.
   Treat current rain, snow, wind, sunshine, cooling, or warming as unconfirmed unless the current
   task explicitly supplies that weather fact. Within each copy mode, do not repeat a
   `source_block_id`. `natural_generate` has no source block, source slot values, or rewrite
   anchors.
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
4. In `source_fill`, fill one compatible block and insert only the current configured campaign
   wording after the complete product passage; never use campaign facts as product components.
   Food-only blocks cannot be filled with beverages, and combination blocks require confirmed
   product components. If compatible blocks or product facts are insufficient, use
   `natural_generate` for the remaining non-rewrite rows without claiming a human source. The source block overrides
   the usual 20/50/30 heuristic. In `human_rewrite`, change the
   concrete situation and wording while staying visibly close to the selected block's vocabulary,
   pauses, repetition, direct questions, or abrupt turns. Avoid tidy explanatory transitions and
   abstract summaries such as “刚好满足需求”, “这个时候很合适”, “具体体验”, or “选择理由”.
   For every rewrite, record at least two retained phrases in `rewrite_anchor_phrases`; each must
   appear verbatim in the final script or batch validation fails. If
   either mode cannot reach 80–100 Chinese characters without invented facts, choose another block
   or request more product facts.
   Before validation, review product-to-need, noun-to-action, coordination level, and closing
   reference. A beverage must not retain hunger/meal reasoning, and “add / add another / comes
   with everything” may coordinate only actual product components.
5. Apply the campaign contract before continuing:
   - every user-confirmed `required` benefit must appear;
   - every `exact_match` benefit must preserve the original wording exactly;
   - every `no_split` benefit must be wrapped as `[[NO_SPLIT]]利益点原文[[/NO_SPLIT]]`;
   - when a platform is supplied, its name must appear exactly in every copy;
   - when no benefit is supplied and no preset is selected, do not invent promotions, amounts,
     thresholds, or platform benefits.
6. Validate every copy before continuing:
   - reject banned words and only the click/purchase calls to action configured for the active
     validation config;
   - use only confirmed product facts;
   - output natural prose, not a title, list, explanation, or Markdown.
   When working from this repository, run `uv run avatar-prompts validate-copy '<copy>'` with
   matching `--benefit-point` arguments or `--preset none`, and revise any failing copy before
   generating its avatar prompt. Sample-inspired copy is not exempt: use the exact current project
   configuration, and never export a candidate that has not passed validation.
7. Remove `[[NO_SPLIT]]` tags before generating an avatar video prompt; they are not spoken text.
   Generate one avatar video prompt per accepted copy. Use the copy as the sole semantic basis.
   Give every prompt a different Chinese young woman and a different outfit. Vary face shape,
   visible facial features, hairstyle, hair color, facial-aesthetic direction, and clothing
   combination while keeping the overall account aesthetic young, natural, clean, and approachable.
   Facial-aesthetic directions may include sweet, cute, cool-clean, elegant mature-sister,
   girl-next-door, and fresh mainstream looks, but must never skew toward auntie, middle-aged,
   elderly, matronly, or old-fashioned looks. Vary outfits across mainstream daily styles such as
   commute, casual, sweet-cool, minimal, and light sporty; avoid exposed, tacky, exaggerated, or
   large-logo clothing.
8. Before export, list an `identity_key` and `outfit_key` for every prompt and verify both are unique
   within the batch. Never use continuity wording such as “same person”, “same face”, “固定人物”,
   or “保持脸部特征一致”.
9. When the user requests an Oceanengine task package, read
   [oceanengine-contract.md](references/oceanengine-contract.md). Derive a static
   `person_prompt` from visible first-frame attributes; do not put temporal camera or lip-sync
   instructions into that image prompt. Keep every static `person_prompt` to 120-180 Chinese
   characters. It must begin with `竖屏9:16，固定中景，手机实拍，数字人口播首帧`,
   say the person is looking directly at the camera using `直视镜头`, state
   `商品不由人物手持`, state `人物不看商品、不接触商品`, and say the scene is only background
   using `场景只作为背景`.
   It must also state `非商品区域无logo` and `无字幕`.
   The product must be placed on the table or countertop in front of the person; never place it
   behind the person, in the background, far away, or off to the side/back.
   Strip `[[NO_SPLIT]]` tags from the CSV `script`; manuscript annotation and CSV export are
   separate operations. Never create or write a CSV merely because a copy was annotated.
   Set each CSV `notes` value to `{actual user category}+{1-based sequence}`. Never write the
   literal placeholder “品类”; for example use `西瓜+1` or `雨伞+1`.
   When the user requests a LibTV OmniHuman package, treat it as a separate output adapter:
   derive `image_prompt` from visible first-frame attributes, derive `audio_prompt` from the
   accepted plain script, and write a per-row LibTV CSV plus a separate interface configuration
   JSON. Keep every `image_prompt` to 120-180 Chinese characters. Every `image_prompt` must
   begin with `竖屏9:16，固定中景，手机实拍，数字人口播首帧`, say the person is looking
   directly at the camera using `直视镜头`, state `商品不由人物手持`, state
   `人物不看商品、不接触商品`, and say the scene is only background using `场景只作为背景`.
   It must also state `非商品区域无logo` and `无字幕`. Do not put LibTV model names,
   node templates, resolution targets, or execution settings into the per-row CSV; those belong
   in `<task>.libtv.interface.json`.
   The product must be placed on the table or countertop in front of the person; never place it
   behind the person, in the background, far away, or off to the side/back.
10. Preview the copy, avatar prompt, static person prompt, product facts, and campaign facts used.
   Require explicit approval
   before any paid video submission.
11. Use the target project's own `preflight` before import. Never silently overwrite an existing
    batch file or blindly resubmit an uncertain task.

When handing generated results to the deterministic CLI, write one JSON manifest that conforms to
`references/generated-task-batch.schema.json`. Run `avatar-prompts validate-batch` before export,
or use `avatar-prompts package`, which performs the same full-batch validation before writing any
selected artifact. The CLI does not generate semantic copy or avatar descriptions and does not call
another model; Codex remains the semantic generator.

For Oceanengine CSV output, never write CSV serialization code or construct CSV rows manually.
Run `avatar-prompts init-batch` once, fill only the generated JSON fields, then run
`avatar-prompts export-csv`. Let the project-owned exporter determine columns, notes, tag removal,
quoting, paths, atomic writes, and overwrite protection.

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
- **LibTV OmniHuman package:** create three independent handoffs from accepted copy/avatar
  results:
  - one UTF-8
    `/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task>.libtv.csv`
    containing per-row task data only (`task_id`, `title`, `notes`, `image_prompt`,
    `audio_prompt`, `voice_label`, `voice_id`, `aspect_ratio`);
  - one UTF-8
    `/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task>.libtv.interface.json`
    containing the LibTV interface, model, node, parameter, naming, voice default, and acceptance
    configuration;
  - one UTF-8
    `/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task>.libtv.plan.md`
    for human review.
  The default semantic voice labels are `温暖闺蜜` for female voices and `温润男声` for male
  voices; `温暖闺蜜` maps to `Chinese (Mandarin)_Warm_Bestie`, and `温润男声` maps to
  `Chinese (Mandarin)_Gentleman`. The default audio constraints are speed `1.2` and volume `8`;
  write volume to the LibTV audio node as schema field `vol`. The target acceptance resolution is
  `720x1280`, but OmniHuman 1.5 currently exposes only `ratio=auto` and `resolution=auto`;
  therefore resolution must be checked after generation. This output must not create a LibTV
  canvas, create nodes, run `libtv node --run`, or submit paid generation.

Preserve all existing CLI arguments by forwarding them unchanged through `scripts/run_cli.py`.
Validate every explicit parameter against `references/cli-parameters.schema.json` or
`references/skill-config.schema.json`, and validate generated task manifests against
`references/generated-task-batch.schema.json`. Preserve requested configuration files, batching, installed
Codex plugins, safe debug output, and all requested output formats. Never remove an existing field,
command, format, hook, or behavior while packaging or installing this skill.

Compatibility defaults:

- If the user asks for 淘宝闪购 without specifying another benefit, use preset
  `taobao-instant-commerce-default`, whose benefit is `最高12元无门槛红包`.
  This preset uses the project-level protected phrase `淘宝闪购有最高12元无门槛红包`; the benefit
  remains required and exact-match, but the `NO_SPLIT` marker wraps the full phrase rather than
  only the redpacket wording.
- If the user provides an explicit benefit, use that benefit instead of the preset.
- If the user says no benefit or no promotion, use `--preset none` semantics and generate without
  any promotional benefit.
- If the user selects the project configuration
  `configs/projects/taobao-instant-commerce-compliance.json`, require the exact benefit `大额红包`
  and use only food-delivery scenarios such as coffee, milk tea, or fried chicken. Follow the
  benefit-forward promotional style, delivery claims, and natural end CTA of the 25-yuan project;
  do not use the 12-yuan project's retail/lifestyle structure. `优惠价`、`活动价`、`福利价` and
  similar fuzzy wording may be used only without a concrete amount. Its validation configuration enables
  `forbid_numeric_redpacket_amounts`; never write an Arabic-numeral or Chinese-numeral redpacket
  amount for this project.
- If the user provides a project configuration file, treat it as the complete project mouthpiece:
  use its product facts, campaign facts, benefit points, forbidden expressions, and disclosures.
  Use its language style to guide tone, viewpoint, sentence rhythm, emphasis, phrases to avoid,
  and extra style rules.
  Use the referenced validation configuration to determine banned expressions, CTA rules,
  character limits, and format rules.
  Do not combine it with the default preset or unrelated campaign arguments.

For batches, keep a one-to-one mapping among source facts, copy, avatar prompt, `task_id`, and output
row. Preserve the full avatar prompt in the audit record even though the current Oceanengine chain
only consumes the static `person_prompt` and `script`, and the current LibTV chain consumes
`image_prompt`, `audio_prompt`, and the separate interface configuration.

## Safety Boundary

- Never invent product or promotion facts.
- Never reuse the same person or the same outfit within a batch.
- Never expose cookies, tokens, browser profiles, signatures, or account identifiers.
- Never trigger `run-api-video` from a general “generate prompts” request.
- Treat import and paid generation as separate user-authorized actions.
