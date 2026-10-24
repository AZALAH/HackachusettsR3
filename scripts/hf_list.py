"""List Hugging Face dataset file sizes without downloading their contents."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import defaultdict


def list_files(repo: str, path: str = "") -> None:
    quoted_path = urllib.parse.quote(path.strip("/"))
    suffix = f"/{quoted_path}" if quoted_path else ""
    url = (
        f"https://huggingface.co/api/datasets/{repo}/tree/main{suffix}"
        "?recursive=true&expand=true"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "datamon/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        items = json.load(response)

    rows = []
    for item in items:
        if item.get("type") == "file":
            size = item.get("size") or (item.get("lfs") or {}).get("size") or 0
            rows.append((item["path"], int(size)))
    rows.sort(key=lambda row: row[1])
    print(
        f"repo: {repo}; path: {path or '/'}; files: {len(rows)}; "
        f"listed total: {sum(size for _, size in rows) / 1e9:.2f} GB"
    )

    by_extension = defaultdict(lambda: [0, 0])
    for filename, size in rows:
        extension = filename.rsplit(".", 1)[-1] if "." in filename else "(none)"
        by_extension[extension][0] += 1
        by_extension[extension][1] += size
    for extension, (count, size) in sorted(
        by_extension.items(), key=lambda item: -item[1][1]
    ):
        print(f"  .{extension:10s} {count:5d} files {size / 1e9:9.3f} GB")

    print("\nSmallest 15 tabular data files")
    data = [row for row in rows if row[0].endswith((".parquet", ".npz", ".csv"))]
    for filename, size in data[:15]:
        print(f"  {size / 1e6:9.2f} MB  {filename}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default="lerobot/droid_100")
    parser.add_argument("path", nargs="?", default="")
    args = parser.parse_args()
    list_files(args.repo, args.path)


if __name__ == "__main__":
    main()
