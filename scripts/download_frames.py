"""Download the bounded, video-free dataset slice used by the demo.

Every source is pinned to an immutable Hugging Face revision and verified by
size and SHA-256. The complete download is under 8 MB; each file and the whole
run also have hard byte limits to prevent accidental large-dataset downloads.
"""

from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_BYTES = 15 * 1024 * 1024
TIMEOUT_SECONDS = 30

BRIDGE_REPO = "IPEC-COMMUNITY/bridge_orig_lerobot"
BRIDGE_REVISION = "0e9d76d07e9df3ea3eba257b2520d4913833fad2"
DROID_REPO = "lerobot/droid_100"
DROID_REVISION = "87301a2d2e99340e2010c9ef0f1d8e780b08aaf9"


@dataclass(frozen=True)
class Asset:
    repo: str
    revision: str
    remote_path: str
    local_path: str
    size: int
    sha256: str


ASSETS = [
    Asset(BRIDGE_REPO, BRIDGE_REVISION, "meta/info.json",
          "bridge_v2/meta/info.json", 4579,
          "14fc7b0ae473266a2c7ee461cfb6d3d621f03ec4f51611cda07498d17eb57291"),
    Asset(BRIDGE_REPO, BRIDGE_REVISION, "meta/episodes.jsonl",
          "bridge_v2/meta/episodes.jsonl", 4351502,
          "39043e8ffb580c02e9b884abd67f31dd5d1b87cdb763332b7957a1101e4c6952"),
    Asset(DROID_REPO, DROID_REVISION, "meta/info.json",
          "droid_100/meta/info.json", 3183,
          "6718973f1f5a5ca76cfdfdddafc177da83636d1a38e50aedca37c090991d5d78"),
    Asset(DROID_REPO, DROID_REVISION, "meta/episodes/chunk-000/file-000.parquet",
          "droid_100/meta/episodes/chunk-000/file-000.parquet", 137686,
          "a22cd872be7140555b7f8dfa6c34ff64642b0308d933c9aa658a89b69746fbbb"),
    Asset(DROID_REPO, DROID_REVISION, "data/chunk-000/file-000.parquet",
          "droid_100/data/chunk-000/file-000.parquet", 2696695,
          "8ce5831e998d9e9b1d743fe42f91dbb654e4172069354de50aa0de874b3bebc8"),
]

for episode, size, digest in (
    (0, 5733, "14ef3d742724ad34701136e1dd4709c965ae98066b2fc88a7a26e960d55520a8"),
    (4, 7465, "4f78fe0d4919974f08a92f20ed38610980c7a9d2d6d6669c002eb0c77f0ae553"),
    (11, 7084, "bad4fea169a9923055242f9c2fe119e9a92cb09080526b22a9d01ad26ea11de4"),
    (15, 10854, "6bb0d934e8884efe01c1f590d10ec71523e009c91d619797c9906c1945d515c6"),
    (395, 3768, "6e165d61298293a8a77c27ee7f97ccd264bb15aa5277bdceca96623b8fc58031"),
):
    name = f"episode_{episode:06d}.parquet"
    ASSETS.append(Asset(
        BRIDGE_REPO, BRIDGE_REVISION, f"data/chunk-000/{name}",
        f"bridge_v2/data/chunk-000/{name}", size, digest,
    ))


def _url(asset: Asset) -> str:
    return (
        f"https://huggingface.co/datasets/{asset.repo}/resolve/"
        f"{asset.revision}/{asset.remote_path}"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(asset: Asset, root: Path) -> None:
    if asset.size > MAX_FILE_BYTES:
        raise ValueError(f"refusing {asset.remote_path}: exceeds per-file limit")
    destination = root / asset.local_path
    if (destination.is_file() and destination.stat().st_size == asset.size
            and _sha256(destination) == asset.sha256):
        print(f"  verified: {asset.local_path} ({asset.size / 1e6:.2f} MB)")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    request = urllib.request.Request(_url(asset), headers={"User-Agent": "datamon/0.1"})
    digest = hashlib.sha256()
    received = 0
    print(f"  download: {asset.local_path} ({asset.size / 1e6:.2f} MB)")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response, \
                temporary.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > MAX_FILE_BYTES or received > asset.size:
                    raise ValueError(f"{asset.remote_path} exceeded its declared size")
                digest.update(chunk)
                handle.write(chunk)
        if received != asset.size:
            raise ValueError(
                f"{asset.remote_path}: expected {asset.size} bytes, received {received}"
            )
        if digest.hexdigest() != asset.sha256:
            raise ValueError(f"{asset.remote_path}: SHA-256 verification failed")
        os.replace(temporary, destination)
    except (OSError, urllib.error.URLError, ValueError) as error:
        raise RuntimeError(f"failed to download {asset.remote_path}: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    total = sum(asset.size for asset in ASSETS)
    if total > MAX_TOTAL_BYTES:
        raise RuntimeError(
            f"download manifest is {total / 1e6:.1f} MB, above the total safety cap"
        )
    root = Path("data/lerobot")
    print(f"Downloading {len(ASSETS)} verified files ({total / 1e6:.2f} MB); no video.")
    for asset in ASSETS:
        fetch(asset, root)
    print("Dataset slice is ready under data/lerobot/.")


if __name__ == "__main__":
    main()
