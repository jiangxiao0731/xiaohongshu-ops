#!/usr/bin/env python3
"""
extract_top_creators.py — Extract top 20 unique creator IDs from today's scraped CSVs.

Usage:
    python3 extract_top_creators.py <data_dir> <date>

Outputs comma-separated user_ids to stdout (consumed by weekly_scrape.sh).
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict


def safe_int(value) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_top_creators.py <data_dir> <date>", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(sys.argv[1])
    target_date = sys.argv[2]

    # Aggregate engagement by user_id
    creators: dict[str, dict] = defaultdict(lambda: {
        "nickname": "",
        "total_liked": 0,
        "total_collected": 0,
        "post_count": 0,
    })

    csv_count = 0
    for csv_file in sorted(data_dir.glob(f"{target_date}-*.csv")):
        # Skip creator CSVs
        if "creators" in csv_file.name:
            continue
        csv_count += 1
        try:
            with open(csv_file, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user_id = row.get("user_id", "").strip()
                    if not user_id:
                        continue
                    entry = creators[user_id]
                    entry["nickname"] = row.get("nickname", "") or entry["nickname"]
                    entry["total_liked"] += safe_int(row.get("liked_count"))
                    entry["total_collected"] += safe_int(row.get("collected_count"))
                    entry["post_count"] += 1
        except Exception as exc:
            print(f"Warning: failed to parse {csv_file}: {exc}", file=sys.stderr)

    if not creators:
        print(f"No creator data found in {csv_count} CSVs for {target_date}", file=sys.stderr)
        sys.exit(0)

    # Rank by total engagement (liked + collected)
    ranked = sorted(
        creators.items(),
        key=lambda x: x[1]["total_liked"] + x[1]["total_collected"],
        reverse=True,
    )

    # Take top 20
    top_ids = [uid for uid, _ in ranked[:20]]

    print(f"Found {len(creators)} unique creators from {csv_count} CSVs, returning top {len(top_ids)}", file=sys.stderr)
    print(",".join(top_ids))


if __name__ == "__main__":
    main()
