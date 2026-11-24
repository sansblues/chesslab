"""Download the data of the experiments from official public sources into data/.

    python -m chesslab.data [--verify] [group ...]     groups: lichess broadcast fide syzygy stockfish

A file already in data/ is kept, so a run resumes where the last one stopped. Each new file
is checked against the size or checksum that its source publishes; --verify checks the files
already present again.
"""
import argparse
import hashlib
import shutil
import sys
import tarfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from chesslab import DATA

LICHESS_URL = "https://database.lichess.org"
LICHESS_FILE = "standard/lichess_db_standard_rated_2026-10.pgn.zst"
LICHESS_SIZE = 30_982_323_881  # bytes; the byte ranges are cut from this file
CHUNKS, CHUNK_SIZE = 48, 24_000_000
MONTHS = [f"{y}-{m:02}" for y, m in [(2024, m) for m in range(7, 13)] + [(2025, m) for m in range(1, 13)]
          + [(2026, m) for m in range(1, 11)]]
FIDE_URL = "https://ratings.fide.com/download"
FIDE_LISTS = ["jul23", "jan24", "jul24", "oct24", "jan25", "apr25", "jul25", "oct25", "jan26", "apr26", "jul26",
              "oct26", "nov26"]
SYZYGY_URL = "https://tablebase.lichess.ovh/tables/standard"
# The 60 six-piece WDL tables that hold most six-piece positions played in the Lichess and broadcast games.
SYZYGY_6 = """KBPPPvK KBPPvKB KBPPvKN KBPPvKP KBPPvKR KBPvKBP KBPvKNP KBPvKPP KNPPPvK KNPPvKB KNPPvKN KNPPvKP
    KNPPvKR KNPvKNP KNPvKPP KPPPPvK KPPPvKB KPPPvKN KPPPvKP KPPPvKQ KPPPvKR KPPvKPP KQBPPvK KQBPvKP KQNPPvK
    KQNPvKP KQPPPvK KQPPvKP KQPPvKQ KQPPvKR KQPvKPP KQPvKQP KQPvKRP KQQBPvK KQQPPvK KQQPvKP KQRBPvK KQRPPvK
    KQRPvKP KQRPvKR KRBPPvK KRBPvKP KRBPvKR KRBvKRP KRNPPvK KRNPvKR KRNvKRP KRPPPvK KRPPvKB KRPPvKN KRPPvKP
    KRPPvKQ KRPPvKR KRPvKBP KRPvKNP KRPvKPP KRPvKRP KRRPPvK KRRPvKR KRRvKRP""".split()
STOCKFISH_URL = "https://github.com/official-stockfish/Stockfish/releases/download/sf_19"
STOCKFISH_TAR = "stockfish-linux-x86-64-universal.tar.gz"
STOCKFISH_SHA256 = "9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f"
STOCKFISH = DATA / "stockfish" / "stockfish"


@dataclass
class File:
    path: Path
    url: str
    start: int | None = None  # first byte of a byte range; None: the whole file
    size: int | None = None
    sha256: str | None = None


def lichess():
    return [File(DATA / "lichess" / "2026-10" / f"chunk_{i:02}.bin", f"{LICHESS_URL}/{LICHESS_FILE}",
                 start=LICHESS_SIZE // CHUNKS * i, size=CHUNK_SIZE) for i in range(CHUNKS)]


def broadcast():
    sums = _checksums(f"{LICHESS_URL}/broadcast/sha256sums.txt")
    names = [f"lichess_db_broadcast_{m}.pgn.zst" for m in MONTHS]
    return [File(DATA / "broadcast" / n, f"{LICHESS_URL}/broadcast/{n}", sha256=sums[n]) for n in names]


def fide():
    return [File(DATA / "fide" / f"standard_{m}frl.zip", f"{FIDE_URL}/standard_{m}frl.zip") for m in FIDE_LISTS]


def syzygy():
    sums = _checksums(f"{SYZYGY_URL}/sha256")
    files = []
    for name, sha256 in sums.items():
        table, kind = name.split(".")
        pieces = len(table) - 1
        if pieces <= 5 or (pieces == 6 and kind == "rtbw" and table in SYZYGY_6):
            folder = f"{'3-4-5' if pieces <= 5 else '6'}-{'wdl' if kind == 'rtbw' else 'dtz'}"
            files.append(File(DATA / "syzygy" / name, f"{SYZYGY_URL}/{folder}/{name}", sha256=sha256))
    return files


def stockfish():
    return [File(DATA / "stockfish" / STOCKFISH_TAR, f"{STOCKFISH_URL}/{STOCKFISH_TAR}", sha256=STOCKFISH_SHA256)]


GROUPS = {"lichess": lichess, "broadcast": broadcast, "fide": fide, "syzygy": syzygy, "stockfish": stockfish}


def fetch(file: File, verify: bool) -> str:
    """Download a file unless it is there. Returns what was done."""
    if file.path.exists():
        if verify:
            _check(file, file.path)
        return "kept"
    part = file.path.with_name(file.path.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 11):
        try:
            _download(file, part)
            break
        except OSError as e:  # network errors and timeouts: resume
            if attempt == 10 or isinstance(e, urllib.error.HTTPError) and e.code < 500:
                raise
            print(f"retry {attempt}: {file.path.name}: {e}", file=sys.stderr)
            time.sleep(5 * attempt)
    _check(file, part)
    part.rename(file.path)
    return "downloaded"


def _download(file, part):
    have = part.stat().st_size if part.exists() else 0
    if have and have == file.size:
        return
    headers = {"User-Agent": "chesslab"}
    if file.start is not None:
        headers["Range"] = f"bytes={file.start + have}-{file.start + file.size - 1}"
    elif have:
        headers["Range"] = f"bytes={have}-"
    try:
        response = urllib.request.urlopen(urllib.request.Request(file.url, headers=headers), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 416 and have:  # nothing left to fetch
            return
        raise
    with response, open(part, "ab") as f:
        if "Range" in headers and response.status != 206:
            raise RuntimeError(f"{file.url}: the server ignored the byte range")
        shutil.copyfileobj(response, f, 1 << 20)


def _check(file, path):
    if file.size is not None and path.stat().st_size != file.size:
        raise RuntimeError(f"{path}: {path.stat().st_size} bytes, expected {file.size}")
    if file.sha256 is not None:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while block := f.read(1 << 24):
                h.update(block)
        if h.hexdigest() != file.sha256:
            raise RuntimeError(f"{path}: SHA-256 differs from the source's")


def _checksums(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "chesslab"}), timeout=60) as r:
        return {name: sha for sha, name in (line.split() for line in r.read().decode().splitlines() if line)}


def _lichess_size():
    request = urllib.request.Request(f"{LICHESS_URL}/{LICHESS_FILE}", method="HEAD", headers={"User-Agent": "chesslab"})
    with urllib.request.urlopen(request, timeout=60) as r:
        return int(r.headers["Content-Length"])


def _install_stockfish():
    if STOCKFISH.exists():
        return
    with tarfile.open(DATA / "stockfish" / STOCKFISH_TAR) as tar:
        binary = tar.extractfile(f"stockfish/{STOCKFISH_TAR.removesuffix('.tar.gz')}")
        with open(STOCKFISH.with_suffix(".part"), "wb") as f:
            shutil.copyfileobj(binary, f)
    STOCKFISH.with_suffix(".part").chmod(0o755)
    STOCKFISH.with_suffix(".part").rename(STOCKFISH)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("groups", nargs="*", metavar="group", help=" ".join(GROUPS) + " (default: all)")
    parser.add_argument("--verify", action="store_true", help="check the files already present too")
    args = parser.parse_args()
    if unknown := set(args.groups) - set(GROUPS):
        parser.error(f"unknown group: {' '.join(unknown)}")
    for group in args.groups or GROUPS:
        files = GROUPS[group]()
        if group == "lichess" and any(not f.path.exists() for f in files) and _lichess_size() != LICHESS_SIZE:
            raise RuntimeError("the Lichess Oct 2026 file changed size: the byte ranges would differ")
        with ThreadPoolExecutor(4) as pool:
            done = list(pool.map(lambda f: fetch(f, args.verify), files))
        if group == "stockfish":
            _install_stockfish()
        print(f"{group}: {done.count('downloaded')} downloaded, {done.count('kept')} kept"
              + (", all verified" if args.verify else ""))


if __name__ == "__main__":
    main()
