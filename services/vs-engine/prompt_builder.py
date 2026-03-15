# services/vs-engine/prompt_builder.py
"""VS prompt construction for the Verbalized Sampling engine."""

from config import CONFIDENCE_FRAMINGS

VS_TEMPLATE = """You are asked to provide {k} distinct responses to the following prompt.
Each response should represent a genuinely different approach or perspective.

IMPORTANT: Assign a {framing} value to each response, representing
how likely you believe it is to be the best answer. Distribute your
{framing} as uniformly as possible — aim for each value to be
near {tau} (approximately {approx_uniform}). Avoid concentrating {framing}
on any single response. The values must sum to 1.0.

Respond in this exact JSON format:
{{
  "responses": [
    {{"content": "your response text here", "{framing}": 0.XX}},
    ...
  ]
}}

Do not include any text outside the JSON object.

--- PROMPT ---
{user_prompt}"""


def build_vs_prompt(
    user_prompt: str,
    k: int,
    tau: float,
    confidence_framing: str = "confidence",
    system_prompt: str | None = None,
) -> str:
    framing = CONFIDENCE_FRAMINGS.get(confidence_framing, confidence_framing)
    approx_uniform = f"1/{k} = {1/k:.2f}"
    vs_prompt = VS_TEMPLATE.format(
        k=k, framing=framing, tau=tau, approx_uniform=approx_uniform, user_prompt=user_prompt,
    )
    if system_prompt:
        return f"{system_prompt}\n\n{vs_prompt}"
    return vs_prompt
