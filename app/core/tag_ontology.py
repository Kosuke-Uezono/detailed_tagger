from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional


@dataclass(frozen=True)
class DetailItem:
    name: str
    shortcut: Optional[str] = None


@dataclass(frozen=True)
class ButtonItem:
    name: str
    details: List[DetailItem]


@dataclass(frozen=True)
class TabItem:
    name: str
    buttons: List[ButtonItem]


class TagOntology:
    """
    Holds tag hierarchy and shortcut mappings loaded from a JSON configuration file.
    Provides accessors for UI generation.
    """

    def __init__(self) -> None:
        self.tabs: List[TabItem] = []
        self.shortcuts: Dict[str, str] = {}
        # Map from shortcut to (lv1, lv2, lv3)
        self.detail_shortcuts: Dict[str, Tuple[str, str, str]] = {}

    def load(self, json_path: str) -> None:
        """Load ontology data from a JSON file."""
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        self.shortcuts = data.get("shortcuts", {}) or {}
        tabs: List[TabItem] = []
        detail_shortcuts: Dict[str, Tuple[str, str, str]] = {}
        for t in data.get("tabs", []):
            lv1 = t.get("name")
            buttons: List[ButtonItem] = []
            for b in t.get("buttons", []):
                lv2 = b.get("name")
                details: List[DetailItem] = []
                for d in b.get("details", []):
                    lv3 = d.get("name")
                    shortcut = d.get("shortcut")
                    details.append(DetailItem(name=lv3, shortcut=shortcut))
                    if shortcut:
                        detail_shortcuts[shortcut] = (lv1, lv2, lv3)
                buttons.append(ButtonItem(name=lv2, details=details))
            tabs.append(TabItem(name=lv1, buttons=buttons))
        self.tabs = tabs
        self.detail_shortcuts = detail_shortcuts