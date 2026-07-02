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
   For CLI, configuration, batching, plugins, debug output, or output-format requests, also read
   [runtime.md](references/runtime.md) and its linked schemas.
2. Normalize the user's facts into:
   - category;
   - product name, if supplied;
   - confirmed selling points;
   - forbidden or unknown claims;
   - requested quantity, defaulting to one.
3. If only a category is supplied, generate a draft using generic situations and observable
   category-level properties. Do not invent material, performance, price, brand, sales, efficacy,
   or promotion facts. State briefly that product-specific claims require review.
4. Generate each 80–120 Chinese-character spoken copy as one concrete, continuous slice of life,
   not a fixed scene-concern-benefit-features-ending sequence. Prefer visible actions and specific
   details over abstract claims. For a batch, vary the person's immediate task, the detail that
   triggers demand, the benefit transition, product interaction, and the final beat.
5. Validate every copy before continuing:
   - preserve
     `[[NO_SPLIT]]淘宝闪购最高12元无门槛红包[[/NO_SPLIT]]` exactly; the tags are
     subtitle-segmentation control metadata and do not count as spoken characters;
   - reject banned words and click/purchase calls to action;
   - use only confirmed product facts;
   - output natural prose, not a title, list, explanation, or Markdown.
   When working from this repository, run `uv run avatar-prompts validate-copy '<copy>'` and
   revise any failing copy before generating its avatar prompt.
6. Remove `[[NO_SPLIT]]` tags before generating an avatar video prompt; they are not spoken text.
   Generate one avatar video prompt per accepted copy. Use the copy as the sole semantic basis.
   Give every prompt a different person and a different outfit. Vary face shape, visible facial
   features, hairstyle, hair color, and clothing combination while keeping the overall account
   aesthetic young, natural, clean, and approachable.
7. Before export, list an `identity_key` and `outfit_key` for every prompt and verify both are unique
   within the batch. Never use continuity wording such as “same person”, “same face”, “固定人物”,
   or “保持脸部特征一致”.
8. When the user requests an Oceanengine task package, read
   [oceanengine-contract.md](references/oceanengine-contract.md). Derive a static
   `person_prompt` from visible first-frame attributes; do not put temporal camera or lip-sync
   instructions into that image prompt.
   Strip `[[NO_SPLIT]]` tags from the CSV `script`; manuscript annotation and CSV export are
   separate operations. Never create or write a CSV merely because a copy was annotated.
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
- **Task package:** create two independent handoffs from the same accepted result:
  - one UTF-8 `<task_id>.smartsplit.txt` per task, preserving `[[NO_SPLIT]]`;
  - one batch UTF-8 CSV for Oceanengine, stripping `[[NO_SPLIT]]` from every `script`.
  Writing either handoff must not invoke, create, overwrite, import, or run the other consumer.
  Run Oceanengine preflight only when the user requests that CSV workflow.

Preserve all existing CLI arguments by forwarding them unchanged through `scripts/run_cli.py`.
Validate every explicit parameter against `references/cli-parameters.schema.json` or
`references/skill-config.schema.json`. Preserve requested configuration files, batching, installed
Codex plugins, safe debug output, and all requested output formats. Never remove an existing field,
command, format, hook, or behavior while packaging or installing this skill.

For batches, keep a one-to-one mapping among source facts, copy, avatar prompt, `task_id`, and output
row. Preserve the full avatar prompt in the audit record even though the current Oceanengine chain
only consumes the static `person_prompt` and `script`.

## Safety Boundary

- Never invent product or promotion facts.
- Never reuse the same person or the same outfit within a batch.
- Never expose cookies, tokens, browser profiles, signatures, or account identifiers.
- Never trigger `run-api-video` from a general “generate prompts” request.
- Treat import and paid generation as separate user-authorized actions.
