#!/usr/bin/env python3
"""Package exactly one clean committed source tree; never include local secrets."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New output directory outside the repository')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise SystemExit('Release output must be outside the repository.')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise SystemExit('Commit all reviewed source changes before packaging.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    archive = output / 'release.tar'
    with archive.open('xb') as destination:
        subprocess.run(['git', 'archive', '--format=tar', '--prefix=release-'+commit+'/', commit],
                       cwd=ROOT, stdout=destination, check=True)
    manifest = {'source_commit': commit, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'archive': archive.name, 'purpose': 'Existing synthetic demo; no access-policy changes'}
    (output / 'release.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
