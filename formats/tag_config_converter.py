"""
CSV→JSON タグ設定コンバータ
==============================

このモジュールは、タグ設定を CSV 形式からアプリが利用する JSON 形式へ変換するための
コマンドラインツールです。CSV ファイルは次のような列構成を想定します。

- ``lv1``: 第1階層のタブ名
- ``lv2``: 第2階層のボタン名
- ``lv3``: 第3階層の詳細タグ名
- ``shortcut`` (任意): 第3階層タグに割り当てるショートカットキー

各行が 1 つの詳細タグを表し、同じ ``lv1``/``lv2`` に属する行がグループ化されて
ボタンや詳細リストを生成します。ショートカットキーは重複しないことを推奨します。

Usage::

    python -m detailed_tagger.formats.tag_config_converter input.csv output.json

ライブラリとして ``convert_csv_to_json`` 関数を直接呼び出すこともできます。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


def convert_csv_to_json(
    input_csv: str,
    output_json: str,
    *,
    auto_shortcuts: bool = False,
    reserved_keys: Optional[List[str]] = None,
) -> None:
    """Convert a CSV file describing tag hierarchy into a JSON configuration file.

    Args:
        input_csv: Path to the CSV file containing columns lv1, lv2, lv3, shortcut.
        output_json: Path to the JSON file to write.
        auto_shortcuts: If True, automatically assign shortcut keys to rows where
            no ``shortcut`` value is provided. Keys will be assigned in a
            deterministic order from a predefined list of candidate key strings.
        reserved_keys: Optional list of keys to exclude from automatic assignment
            (e.g. keys already used by global actions or reserved by the app).

    The resulting JSON will follow the schema used by ``TagOntology``. It will
    contain a ``version`` key, a list of ``tabs`` representing level 1 tabs, and
    an empty ``shortcuts`` object (global action shortcuts can be edited manually).

    When ``auto_shortcuts`` is enabled, each detail tag that lacks a shortcut in
    the CSV will be assigned the next available key from the candidate list.
    ``reserved_keys`` can be used to prevent assignment of keys that are already
    bound elsewhere (e.g. in a user-defined ``shortcuts`` section).
    """
    in_path = Path(input_csv)
    out_path = Path(output_json)
    if reserved_keys is None:
        reserved_keys = []
    # Candidate key sequences for automatic assignment. Adjust as needed.
    candidate_keys = [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "0",
        "Q",
        "W",
        "E",
        "R",
        "T",
        "Y",
        "U",
        "I",
        "O",
        "P",
        "A",
        "S",
        "D",
        "F",
        "G",
        "H",
        "J",
        "K",
        "L",
        "Z",
        "X",
        "C",
        "V",
        "B",
        "N",
        "M",
    ]
    # Track used shortcuts to avoid duplicates
    used_keys = set(reserved_keys)
    tags: Dict[str, Dict[str, List[Dict[str, Optional[str]]]]] = {}
    shortcuts_map: Dict[str, tuple[str, str, str]] = {}
    # Read CSV and build hierarchy
    with in_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lv1 = (row.get("lv1") or "").strip()
            lv2 = (row.get("lv2") or "").strip()
            lv3 = (row.get("lv3") or "").strip()
            shortcut = (row.get("shortcut") or "").strip()
            if not (lv1 and lv2 and lv3):
                # Skip incomplete rows
                continue
            grp = tags.setdefault(lv1, {})
            detail_list = grp.setdefault(lv2, [])
            # Determine shortcut: either provided or auto-assigned
            assigned_key: Optional[str] = None
            if shortcut:
                assigned_key = shortcut
            elif auto_shortcuts:
                # Assign next available candidate key
                for cand in candidate_keys:
                    if cand not in used_keys:
                        assigned_key = cand
                        used_keys.add(cand)
                        break
            detail_entry: Dict[str, Optional[str]] = {"name": lv3}
            if assigned_key:
                detail_entry["shortcut"] = assigned_key
                shortcuts_map[assigned_key] = (lv1, lv2, lv3)
            detail_list.append(detail_entry)
    # Build JSON structure
    data: Dict[str, object] = {
        "version": "1.0",
        "tabs": [],
        "shortcuts": {},  # global shortcuts can be edited manually
    }
    for lv1, lv2s in tags.items():
        tab_obj: Dict[str, object] = {"name": lv1, "buttons": []}
        for lv2, details in lv2s.items():
            btn_obj: Dict[str, object] = {"name": lv2, "details": []}
            for detail in details:
                # Remove empty shortcut entries from JSON
                if "shortcut" in detail and not detail["shortcut"]:
                    detail = {"name": detail["name"]}
                btn_obj["details"].append(detail)
            tab_obj["buttons"].append(btn_obj)
        data["tabs"].append(tab_obj)
    # Write JSON file
    with out_path.open("w", encoding="utf-8") as out_f:
        json.dump(data, out_f, ensure_ascii=False, indent=2)
    # Optionally print summary of assigned keys
    if auto_shortcuts:
        assigned_count = len([k for k in used_keys if k not in reserved_keys])
        print(
            f"Converted {in_path} -> {out_path}. Tags: {len(tags)} lv1 items."
            f" Auto-assigned shortcuts for {assigned_count} tags."
        )
    else:
        print(f"Converted {in_path} -> {out_path}. Tags: {len(tags)} lv1 items.")


def _main(argv: list[str]) -> int:
    """Entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Convert a CSV file describing tag hierarchy into a JSON tag config.\n"
            "Columns: lv1, lv2, lv3, shortcut."
        )
    )
    parser.add_argument("input_csv", help="Path to the input CSV file")
    parser.add_argument("output_json", help="Path to the output JSON file")
    parser.add_argument(
        "--auto-shortcuts",
        action="store_true",
        help="Automatically assign shortcut keys to tags that have none",
    )
    args = parser.parse_args(argv[1:])
    convert_csv_to_json(
        args.input_csv,
        args.output_json,
        auto_shortcuts=args.auto_shortcuts,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))