"""Prompt factory for verse classification (Fase 1, paso 2).

Centralizes the single prompt template so it is easy to tweak without touching
the classify pipeline. Everything the model must produce is in English, and the
tags themselves are English to avoid translation overhead for the small model.

The model is asked to classify with AT MOST 2 tags and to fall back to "hope" if
it is a promise that fits no tag. One-shot (a worked example) is included to
improve the small model's compliance with the strict JSON shape.
"""

# Canonical English tags. These are the exact tokens persisted to SQLite and
# matched by the CLI. Keep them lowercase and consistent.
TAGS = [
    "provision",
    "protection",
    "healing",
    "wisdom",
    "justice",
    "peace",
    "comfort",
    "strength",
    "companionship",
    "hope",
    "forgiveness",
    "love",
    "faith",
    "salvation",
    "purpose",
]

TAGS_JOINED = ", ".join(TAGS)

# One-shot examples shown to the model to help it stay inside the JSON schema.
_EXAMPLE_INPUT = (
    "And my God will supply every need of yours according to his riches in "
    "glory in Christ Jesus. (Philippians 4:19)"
)
_EXAMPLE_OUTPUT = '{"is_promise": true, "tags": ["provision"]}'

_TEMPLATE = """\
You are a biblical theologian. Analyze the following Bible verse and decide
whether it contains an explicit or implicit promise FROM God.

Rules:
- If it is a promise, set "is_promise" to true and classify it with AT MOST 2
  of these exact tags: {tags}.
- If it is a promise but fits none of the tags, use "hope".
- If it is NOT a promise from God (e.g. a judgment, a warning, a historical
  account, or a human's words), set "is_promise" to false and "tags" to [].
- Respond ONLY with valid JSON. No other text, no markdown, no explanations.

Return this exact JSON shape:
{{"is_promise": true, "tags": ["tag1", "tag2"]}}

Example:
Verse: {example_input}
Answer: {example_output}

Now analyze this verse:
({reference})
"""


def build_prompt(text: str, reference: str) -> str:
    """Build the classification prompt for a single verse."""
    return _TEMPLATE.format(
        tags=TAGS_JOINED,
        example_input=_EXAMPLE_INPUT,
        example_output=_EXAMPLE_OUTPUT,
        reference=f"{reference}\n{text}" if reference else text,
    )
