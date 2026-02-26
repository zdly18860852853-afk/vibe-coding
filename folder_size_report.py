#!/usr/bin/env python3
"""
Scan folders under C:\\, compute recursive directory sizes, and print results.

Examples:
  python folder_size_report.py
  python folder_size_report.py --root C:\\ --top 100
  python folder_size_report.py --tree --top 30
"""

from __future__ import annotations

import argparse
import heapq
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


def walk_and_collect(root: str) -> Tuple[Dict[str, int], Dict[str, List[str]], int]:
    # own_size stores only direct file sizes in each directory.
    own_size: Dict[str, int] = defaultdict(int)
    children: Dict[str, List[str]] = defaultdict(list)
    visited_dirs = 0

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        visited_dirs += 1
        abs_dir = os.path.abspath(dirpath)

        # Keep parent-child mapping for tree output.
        for name in dirnames:
            child = os.path.join(abs_dir, name)
            children[abs_dir].append(child)

        # Sum direct file sizes inside current directory.
        for filename in filenames:
            file_path = os.path.join(abs_dir, filename)
            try:
                own_size[abs_dir] += os.path.getsize(file_path)
            except (OSError, PermissionError):
                # Skip files we cannot access.
                continue

    # total_size stores recursive directory sizes.
    total_size: Dict[str, int] = dict(own_size)

    # Post-order aggregation: larger depth first.
    all_dirs = set(total_size) | set(children)
    for directory in sorted(all_dirs, key=lambda p: p.count(os.sep), reverse=True):
        parent = os.path.dirname(directory.rstrip("\\/"))
        if parent and directory != parent:
            total_size[parent] = total_size.get(parent, 0) + total_size.get(directory, 0)

    # Ensure all discovered directories exist in total_size.
    for d in all_dirs:
        total_size.setdefault(d, 0)

    return total_size, children, visited_dirs


def print_top(top_items: List[Tuple[str, int]], total_count: int) -> None:
    print(f"\nTop {len(top_items)} directories by recursive size:")
    print("-" * 96)
    print(f"{'Rank':>4}  {'Size':>12}  Path")
    print("-" * 96)
    for idx, (path, size) in enumerate(top_items, start=1):
        print(f"{idx:>4}  {human_size(size):>12}  {path}")


def build_largest_child_map(children: Dict[str, List[str]], total_size: Dict[str, int]) -> Dict[str, List[str]]:
    ordered: Dict[str, List[str]] = {}
    for parent, child_list in children.items():
        ordered[parent] = sorted(
            child_list,
            key=lambda c: total_size.get(c, 0),
            reverse=True,
        )
    return ordered


def print_tree(
    root: str,
    children: Dict[str, List[str]],
    total_size: Dict[str, int],
    depth_limit: int,
    per_level_limit: int,
) -> None:
    ordered_children = build_largest_child_map(children, total_size)
    root_abs = os.path.abspath(root)

    def _print_node(node: str, prefix: str, depth: int, is_last: bool) -> None:
        if depth == 0:
            line_prefix = ""
            child_prefix = ""
        else:
            line_prefix = prefix + ("└── " if is_last else "├── ")
            child_prefix = prefix + ("    " if is_last else "│   ")

        print(f"{line_prefix}{Path(node).name or node} ({human_size(total_size.get(node, 0))})")
        if depth >= depth_limit:
            return

        child_nodes = ordered_children.get(node, [])[:per_level_limit]
        for i, child in enumerate(child_nodes):
            _print_node(
                child,
                child_prefix,
                depth + 1,
                is_last=(i == len(child_nodes) - 1),
            )

    print("\nLargest children tree view:")
    print("-" * 96)
    _print_node(root_abs, "", 0, True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan folders and rank by recursive directory size.")
    parser.add_argument("--root", default=r"C:\\", help="Root path to scan. Default: C:\\")
    parser.add_argument("--top", type=int, default=10, help="Number of largest directories to display.")
    parser.add_argument("--tree", action="store_true", help="Show a tree view for parent-child structure.")
    parser.add_argument("--tree-depth", type=int, default=3, help="Max depth for tree output.")
    parser.add_argument("--tree-children", type=int, default=8, help="Max children per node in tree view.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        raise SystemExit(f"Root path does not exist or is not a directory: {root}")

    print(f"Scanning directory sizes under: {root}")
    print("This can take significant time on large drives...")
    total_size, children, visited_dirs = walk_and_collect(root)
    top_n = max(1, args.top)
    top_items = heapq.nlargest(top_n, total_size.items(), key=lambda x: x[1])

    print(f"\nScanned directories: {visited_dirs}")
    print_top(top_items, len(total_size))

    if args.tree:
        print_tree(
            root=root,
            children=children,
            total_size=total_size,
            depth_limit=max(0, args.tree_depth),
            per_level_limit=max(1, args.tree_children),
        )


if __name__ == "__main__":
    main()

#20260227
