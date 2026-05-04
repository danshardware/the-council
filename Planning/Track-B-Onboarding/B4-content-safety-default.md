# B4 — content_safety Guardrail Default + Template Integration

## Overview

The `content_safety` guardrail in `config/guardrails.yaml` currently has placeholder
company-name text (`___, an ___ company`) and won't function correctly for any
deployment.

Fix in two parts:
1. **Default state** — if `data/config/company_info.yaml` doesn't exist, the prompt
   instructs the model to tell the user to run onboarding rather than reviewing content.
2. **Configured state** — once `company_info.yaml` exists (written by B3), the prompt
   uses template substitution to insert the real company name, description, and
   restricted topics.

No code changes — this uses the existing `render_prompt` / `_load_config_dir` system
already in `engine/template.py`.

---

## Type Contracts

### `data/config/company_info.yaml` schema (written by B3/Ops):

```yaml
name: "Acme Corp"
description: "B2B SaaS for HR teams"
restricted_topics:
  - "competitor disparagement"
  - "financial advice without disclaimer"
```

When this file is absent, `config/guardrails.yaml` provides a safe default.  When it
exists, it shadows or extends the base via the existing config layering in `template.py`
(`override_dir` takes priority).

---

## Workflow

### Step 1 — Write two versions of `content_safety` in `config/guardrails.yaml`

Replace the current placeholder prompt with a template that references
`{{config.company_info.name}}` etc.:

```yaml
content_safety: |
  You are a content safety reviewer for {{config.company_info.name}},
  {{config.company_info.description}}.

  Review the proposed content for:

  1. **Brand safety**: Is the content consistent with the company's values?
     Reject promotional hype, false claims, or off-brand content.
  2. **Accuracy risk**: Specific technical claims that may be wrong or misleading?
     If so, flag for review (needs_confirmation), don't reject.
  3. **Restricted topics**: Does the content touch any of the following?
     {{#config.company_info.restricted_topics}}
     - {{.}}
     {{/config.company_info.restricted_topics}}
     If yes, reject.
  4. **Competitor disparagement**: Unfair attacks on named competitors? Reject.

  Respond ONLY with valid YAML:
  ```yaml
  verdict: approved  # approved | needs_confirmation | rejected
  reason: "brief reason"
  ```
```

### Step 2 — Create `config/company_info.yaml` with a safe default

This is the built-in fallback (in `config/`, not `data/config/`).  It ships with the
image and triggers the "not configured" behaviour:

```yaml
# config/company_info.yaml  (shipped with the image — not to be edited by deployers)
name: "an unconfigured Council instance"
description: |
  Content safety is not yet configured for this deployment.
  When asked to review content, tell the user to run the onboarding flow:
    uv run run.py --agent concierge --flow onboarding --prompt "begin onboarding"
  Then return: verdict: needs_confirmation with that message as the reason.
restricted_topics: []
```

When `data/config/company_info.yaml` exists (written by Ops during B3), it takes
priority via the existing layering in `_load_config_dir()`.

---

## Testing Plan (TDD)

File: `tests/test_content_safety_guardrail.py`

```python
def test_content_safety_without_company_info_returns_needs_confirmation():
    """
    Without data/config/company_info.yaml, content_safety must return
    needs_confirmation with a message to run onboarding.
    """
    # Ensure data/config/company_info.yaml does NOT exist.
    # Call call_llm() directly with the rendered content_safety prompt.
    # Assert: verdict == "needs_confirmation"
    # Assert: reason mentions "onboarding"
    from engine.template import _load_config_dir, render_prompt
    _load_config_dir.cache_clear()
    cfg = _load_config_dir()
    prompt = cfg["guardrails"]["content_safety"]
    # Render with a dummy shared state (no company_info key present)
    rendered = render_prompt(prompt, {})
    parsed, _, _ = call_llm(
        model_id="us.amazon.nova-lite-v1:0",
        system_prompt=rendered,
        messages=[{"role": "user", "content": "Post this: Our product is the best!"}],
    )
    assert parsed.get("verdict") == "needs_confirmation"
    assert "onboarding" in parsed.get("reason", "").lower()


def test_content_safety_with_company_info_reviews_correctly():
    """
    With data/config/company_info.yaml present, content_safety reviews
    against real company values.
    """
    # Write a test company_info.yaml to data/config/.
    # Call call_llm with rendered prompt.
    # Assert: a benign post gets approved, a restricted-topic post gets rejected.
    ...
```

---

## Acceptance Criteria

- [ ] `config/company_info.yaml` exists in the repo with safe default content
- [ ] `content_safety` in `config/guardrails.yaml` uses Mustache template variables
      referencing `{{config.company_info.name}}` and `{{config.company_info.description}}`
- [ ] Restricted topics rendered as a list via `{{#config.company_info.restricted_topics}}`
- [ ] Without `data/config/company_info.yaml`, rendered prompt instructs the LLM to
      return `needs_confirmation` with an "run onboarding" reason
- [ ] With `data/config/company_info.yaml`, prompt correctly includes real company info
- [ ] `_load_config_dir()` cache is cleared in tests to pick up fixture files
- [ ] All B4 tests pass

---

## QA Notes

- The existing `render_prompt` / Mustache system supports `{{#list}}{{.}}{{/list}}`
  syntax for arrays — `restricted_topics` is an array, so the Mustache section syntax
  is correct and already supported.
- `_load_config_dir()` uses `functools.lru_cache` — tests must call
  `_load_config_dir.cache_clear()` before each test to force a reload.
- The default `config/company_info.yaml` is shipped in the image.  Deployers must
  NOT edit it — they configure via `data/config/company_info.yaml` (written by Ops).
- Do not add `company_info` to `config/guardrails.yaml` as a nested key — it should
  be a separate file so deployers can version it independently.

---

## Instructions to the Coder

1. Create `config/company_info.yaml` with the default content above.
2. Update the `content_safety` key in `config/guardrails.yaml` to use template vars.
3. Remove (or comment out) the old placeholder text with `___, an ___`.
4. Write and run tests.
5. Confirm `_load_config_dir()` picks up both `config/company_info.yaml` (built-in)
   and `data/config/company_info.yaml` (override) correctly by checking the layering
   logic in `template.py`.
