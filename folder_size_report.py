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
    own_size: Dict[str, int] = defaultdict(int)
    children: Dict[str, List[str]] = defaultdict(list)
    visited_dirs = 0

    stack = [os.path.abspath(root)]
    dirs_visited = []

    while stack:
        current_dir = stack.pop()
        visited_dirs += 1
        dirs_visited.append(current_dir)

        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir():
                            child_path = entry.path
                            children[current_dir].append(child_path)
                            stack.append(child_path)
                        elif entry.is_file():
                            own_size[current_dir] += entry.stat(follow_symlinks=False).st_size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue

    total_size: Dict[str, int] = dict(own_size)

    # Post-order aggregation: reversed stack order ensures children are processed before parents.
    for d in reversed(dirs_visited):
        if d not in total_size:
            total_size[d] = 0
        for child in children.get(d, []):
            total_size[d] += total_size.get(child, 0)

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
