"""Provider adapters + factories selecting one or more by name."""
from __future__ import annotations

import re

from acme_dwh.config import Settings, get_settings
from acme_dwh.ingestion.providers.base import Extractor, RawPoint, SourceDescriptor

__all__ = [
    "Extractor",
    "RawPoint",
    "SourceDescriptor",
    "build_extractor",
    "resolve_providers",
    "ALL_PROVIDERS",
]

# Canonical provider names, plus the aliases accepted on the CLI / API / UI.
ALL_PROVIDERS = ["bitfinex", "nasdaq_data_link"]
_ALIASES = {
    "bitfinex": "bitfinex",
    "nasdaq_data_link": "nasdaq_data_link",
    "ndl": "nasdaq_data_link",
    "nasdaq": "nasdaq_data_link",
    "quandl": "nasdaq_data_link",
}


def resolve_providers(spec: str | list[str] | None = None, settings: Settings | None = None) -> list[str]:
    """Turn a provider spec into an ordered, de-duplicated list of canonical names.

    Accepts a single name, an alias, ``"both"``/``"all"`` (every provider), or a
    comma/space-separated combination (e.g. ``"bitfinex,nasdaq_data_link"``). A
    list of names is also accepted. Falls back to ``settings.ingest_provider``.
    """
    s = settings or get_settings()
    raw = spec if spec is not None else s.ingest_provider
    tokens = raw if isinstance(raw, list) else re.split(r"[\s,]+", str(raw).strip())

    names: list[str] = []
    for token in (t for t in tokens if t):
        low = token.lower()
        if low in ("both", "all"):
            for provider in ALL_PROVIDERS:
                if provider not in names:
                    names.append(provider)
            continue
        canonical = _ALIASES.get(low)
        if canonical is None:
            raise ValueError(
                f"Unknown ingest provider: {token!r} "
                "(use 'bitfinex', 'nasdaq_data_link', or 'both')"
            )
        if canonical not in names:
            names.append(canonical)

    if not names:
        raise ValueError("No ingest provider specified.")
    return names


def build_extractor(provider: str | None = None, settings: Settings | None = None) -> Extractor:
    """Build a single extractor for one canonical provider name (or alias)."""
    s = settings or get_settings()
    name = _ALIASES.get((provider or s.ingest_provider).lower())
    if name == "bitfinex":
        from acme_dwh.ingestion.providers.bitfinex import BitfinexExtractor

        return BitfinexExtractor()
    if name == "nasdaq_data_link":
        from acme_dwh.ingestion.providers.nasdaq_data_link import NasdaqDataLinkExtractor

        return NasdaqDataLinkExtractor(api_key=s.ndl_api_key)
    raise ValueError(f"Unknown ingest provider: {provider!r} (use 'bitfinex' or 'nasdaq_data_link')")
