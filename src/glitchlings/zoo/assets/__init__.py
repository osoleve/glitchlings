"""Compatibility shim for the relocated asset helpers."""

from __future__ import annotations

from glitchlings.assets import (
    PIPELINE_ASSET_SPECS,
    PIPELINE_ASSETS,
    AssetKind,
    PipelineAsset,
    hash_asset,
    load_homophone_groups,
    load_json,
    open_binary,
    open_text,
    read_text,
)

__all__ = [
    "AssetKind",
    "PipelineAsset",
    "PIPELINE_ASSETS",
    "PIPELINE_ASSET_SPECS",
    "hash_asset",
    "load_homophone_groups",
    "load_json",
    "open_binary",
    "open_text",
    "read_text",
]
