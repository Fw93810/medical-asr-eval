"""Download PriMock57 (transcripts, notes, audio).

The GitHub repo stores the .wav files with Git LFS. A plain `git clone`
without git-lfs gives 133-byte pointer files instead of audio. This script:
  1. clones the repo with GIT_LFS_SKIP_SMUDGE=1 (fast; text files only),
  2. downloads each .wav from GitHub's LFS media endpoint
     (https://media.githubusercontent.com/media/babylonhealth/primock57/main/audio/<file>)
     and checks it against the sha256 + size in the pointer file.

Usage:
  python -I scripts/download_data.py --out data/primock57                 # all 57
  python -I scripts/download_data.py --out data/primock57 --limit 3       # first 3
  python -I scripts/download_data.py --out data/primock57 --ids day1_consultation01
"""
import argparse
import hashlib
import os
import subprocess
import sys
import urllib.request

REPO = "https://github.com/babylonhealth/primock57"
MEDIA = "https://media.githubusercontent.com/media/babylonhealth/primock57/main/audio/"


def read_pointer(path):
    """Return (sha256, size) if `path` is a Git LFS pointer file, else None."""
    if os.path.getsize(path) > 1024:
        return None
    with open(path, "r", errors="ignore") as f:
        text = f.read()
    if not text.startswith("version https://git-lfs.github.com/spec/v1"):
        return None
    fields = dict(line.split(" ", 1) for line in text.strip().splitlines())
    return fields["oid"].split(":", 1)[1], int(fields["size"])


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/primock57")
    ap.add_argument("--ids", nargs="*", help="consultation ids, e.g. day1_consultation01")
    ap.add_argument("--limit", type=int, help="only the first N consultations (sorted)")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(args.out, "transcripts")):
        env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
        subprocess.run(["git", "clone", "--depth", "1", REPO, args.out], check=True, env=env)

    audio_dir = os.path.join(args.out, "audio")
    ids = sorted({f.rsplit("_", 1)[0] for f in os.listdir(audio_dir) if f.endswith(".wav")})
    if args.ids:
        ids = [i for i in ids if i in set(args.ids)]
    if args.limit:
        ids = ids[: args.limit]

    for cid in ids:
        for spk in ("doctor", "patient"):
            name = f"{cid}_{spk}.wav"
            path = os.path.join(audio_dir, name)
            ptr = read_pointer(path)
            if ptr is None:
                print(f"[ok]   {name} (already audio)")
                continue
            sha, size = ptr
            tmp = path + ".part"
            print(f"[get]  {name} ({size / 1e6:.1f} MB)")
            urllib.request.urlretrieve(MEDIA + name, tmp)
            if os.path.getsize(tmp) != size or sha256_of(tmp) != sha:
                os.remove(tmp)
                sys.exit(f"checksum mismatch for {name}")
            os.replace(tmp, path)
    print(f"done: {len(ids)} consultations in {audio_dir}")


if __name__ == "__main__":
    main()
