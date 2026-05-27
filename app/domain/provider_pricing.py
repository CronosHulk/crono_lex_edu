from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.provider_settings import DEFAULT_USER_IMPORT_OPENAI_MODEL


@dataclass(frozen=True)
class TokenPricing:
    provider_key: str
    model: str
    input_usd_per_1m: Decimal
    output_usd_per_1m: Decimal
    source: str


OPENAI_PRICING_SOURCE = "https://openai.com/api/pricing/"

TOKEN_PRICING: tuple[TokenPricing, ...] = (
    TokenPricing("openai", "gpt-5.4", Decimal("2.50"), Decimal("15.00"), OPENAI_PRICING_SOURCE),
    TokenPricing(
        "openai",
        DEFAULT_USER_IMPORT_OPENAI_MODEL,
        Decimal("0.75"),
        Decimal("4.50"),
        OPENAI_PRICING_SOURCE,
    ),
)


def find_token_pricing(provider_key: str, model: str) -> TokenPricing | None:
    normalized_provider = provider_key.strip().lower()
    normalized_model = model.strip().lower()
    for item in TOKEN_PRICING:
        if item.provider_key == normalized_provider and item.model.lower() == normalized_model:
            return item
    return None


def estimate_token_cost_usd(
    *,
    provider_key: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    pricing = find_token_pricing(provider_key, model)
    if pricing is None:
        return Decimal("0")
    return (
        Decimal(max(input_tokens, 0)) * pricing.input_usd_per_1m
        + Decimal(max(output_tokens, 0)) * pricing.output_usd_per_1m
    ) / Decimal("1000000")


def list_provider_model_options(provider_key: str) -> list[str]:
    normalized_provider = str(provider_key or "").strip().lower()
    return sorted(
        {item.model for item in TOKEN_PRICING if item.provider_key == normalized_provider},
        key=str.lower,
    )
