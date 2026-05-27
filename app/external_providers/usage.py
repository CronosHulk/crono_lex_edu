from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.provider_pricing import estimate_token_cost_usd


@dataclass(frozen=True)
class ProviderUsage:
    provider_key: str
    model: str
    request_count: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    pricing_source: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_status_json(self) -> dict[str, Any]:
        return {
            "provider_key": self.provider_key,
            "model": self.model,
            "request_count": self.request_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": str(self.estimated_cost_usd),
            "pricing_source": self.pricing_source,
        }


def estimate_text_tokens(value: str) -> int:
    # Conservative enough for cost tracking: roughly 4 chars/token, rounded up.
    return max(math.ceil(len(value or "") / 4), 1)


def openai_usage_from_response(
    *,
    response_json: dict[str, Any],
    model: str,
    prompt_text: str,
    output_text: str,
) -> ProviderUsage:
    usage = response_json.get("usage") if isinstance(response_json.get("usage"), dict) else {}
    input_tokens = _positive_int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or usage.get("total_input_tokens")
    )
    output_tokens = _positive_int(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or usage.get("total_output_tokens")
    )
    if input_tokens <= 0:
        input_tokens = estimate_text_tokens(prompt_text)
    if output_tokens <= 0:
        output_tokens = estimate_text_tokens(output_text)
    return ProviderUsage(
        provider_key="openai",
        model=model,
        request_count=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimate_token_cost_usd(
            provider_key="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        pricing_source="https://openai.com/api/pricing/",
    )


def _positive_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0
