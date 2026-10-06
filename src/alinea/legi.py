"""Download the Code du travail from the @socialgouv/legi-data npm package.

legi-data is a daily JSON extraction of the official LEGI database (Legifrance). We pin one
package version and check its checksum, so a given commit always ingests the same text.
"""

import base64
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

LEGI_DATA_VERSION = "2.570.0"
# sha512 published by the npm registry for that version (`dist.integrity`).
LEGI_DATA_INTEGRITY = "sha512-cM8OZfmqX5qyoW7YR0/qWD52mNu5H0rmqhW+p0qrnw5u3b4lf30MlyFBGAZchUWtb6DAU9bTAYavI+rAXlszbA=="  # noqa: E501
TARBALL_URL = "https://registry.npmjs.org/@socialgouv/legi-data/-/legi-data-{version}.tgz"

# Legifrance id of the Code du travail.
CODE_DU_TRAVAIL = "LEGITEXT000006072050"


def check_integrity(payload: bytes, integrity: str) -> None:
    """Raise if `payload` does not match an npm `sha512-<base64>` integrity string."""
    algo, _, expected = integrity.partition("-")
    actual = base64.b64encode(hashlib.new(algo, payload).digest()).decode()
    if actual != expected:
        raise ValueError(f"checksum mismatch: expected {integrity}, got {algo}-{actual}")


def download_code(data_dir: Path) -> Path:
    """Return the path of the Code du travail JSON, downloading it once per pinned version."""
    target = data_dir / "raw" / f"legi-data-{LEGI_DATA_VERSION}" / f"{CODE_DU_TRAVAIL}.json"
    if target.exists():
        return target

    url = TARBALL_URL.format(version=LEGI_DATA_VERSION)
    with urllib.request.urlopen(url) as response:
        payload = response.read()
    check_integrity(payload, LEGI_DATA_INTEGRITY)

    # Read only the one file we need from the archive, without extracting the rest.
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        member = tar.extractfile(f"package/data/{CODE_DU_TRAVAIL}.json")
        if member is None:
            raise FileNotFoundError(f"{CODE_DU_TRAVAIL}.json not found in {url}")
        content = member.read()

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(content)
    tmp.rename(target)  # atomic: a crash never leaves a half-written file behind
    return target


def load_code(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
