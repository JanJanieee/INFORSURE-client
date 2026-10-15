"""Download the supplied English classifier, or install a saved release ZIP offline."""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import config


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def matches(path: Path, entry: dict) -> bool:
    return path.is_file() and path.stat().st_size == entry['bytes'] and sha256(path) == entry['sha256']


def install(archive: Path | None = None, verify_only: bool = False) -> None:
    manifest = json.loads((config.ROOT / 'models/download.json').read_text(encoding='utf-8'))
    files = manifest['files']
    for name in files:
        destination = (config.MODELS_DIR / name).resolve()
        if not destination.is_relative_to(config.MODELS_DIR.resolve()):
            raise ValueError('Invalid model file path in download manifest')
    if all(matches(config.MODELS_DIR / name, entry) for name, entry in files.items()):
        print(f"Classifier weights verified: {manifest['model_version']}", flush=True)
        return
    if verify_only:
        raise ValueError('Classifier weights are missing or invalid. Run setup-demo.ps1 first.')
    cache = config.ROOT / '.cache/downloads'
    cache.mkdir(parents=True, exist_ok=True)
    if archive is None:
        archive = cache / Path(manifest['url']).name
        if not archive.is_file() or archive.stat().st_size != manifest['archive_bytes'] or sha256(archive) != manifest['archive_sha256']:
            partial = archive.with_suffix('.zip.part')
            print(f"Downloading English classifier ({manifest['archive_bytes'] / 1e9:.2f} GB)...", flush=True)
            request = urllib.request.Request(manifest['url'], headers={'User-Agent': 'InforSure-client'})
            try:
                with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as output:
                    shutil.copyfileobj(response, output, length=1024 * 1024)
                if partial.stat().st_size != manifest['archive_bytes'] or sha256(partial) != manifest['archive_sha256']:
                    raise ValueError('Classifier download checksum failed; rerun setup to retry.')
                os.replace(partial, archive)
            except Exception:
                partial.unlink(missing_ok=True)
                raise
    if archive.stat().st_size != manifest['archive_bytes'] or sha256(archive) != manifest['archive_sha256']:
        raise ValueError('Model ZIP does not match the supplied model checksum.')
    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(files) or len(bundle.namelist()) != len(files):
            raise ValueError('Unexpected files in the model ZIP.')
        for name, entry in files.items():
            destination = config.MODELS_DIR / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.part', delete=False) as output:
                pending = Path(output.name)
                try:
                    with bundle.open(name) as source:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                except Exception:
                    output.close()
                    pending.unlink(missing_ok=True)
                    raise
            try:
                if not matches(pending, entry):
                    raise ValueError('Extracted classifier checksum failed.')
                os.replace(pending, destination)
            finally:
                pending.unlink(missing_ok=True)
    print(f"Classifier installed: {manifest['model_version']}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='use an already downloaded release ZIP')
    parser.add_argument('--verify', action='store_true', help='check local weights without downloading')
    args = parser.parse_args()
    try:
        install(args.archive, args.verify)
    except urllib.error.HTTPError as exc:
        print(f'Model download returned HTTP {exc.code}. For a private repository, download the weights ZIP from its GitHub release in your signed-in browser, place it in the project root, and rerun setup. You can also use setup-demo.ps1 -ModelArchive PATH.')
        return 1
    except Exception as exc:
        print(f'Model setup failed: {exc}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
