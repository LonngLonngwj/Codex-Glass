"""Fetch exact, unmodified upstream sources accompanying the frozen libraries.

Sources are installed locally, so sharing the Setup EXE needs no separate link
or written offer. SHA-256 verification happens before compiler invocation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.request

QT_VERSION = '6.11.2'
QT_MODULES = ('qtbase', 'qtdeclarative', 'qtsvg', 'qtshadertools', 'qtimageformats', 'qttranslations')


def read(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    sources = []
    for package, version in (('PyQt6', '6.11.0'), ('PyQt6-sip', '13.12.0'),
                             ('psutil', '7.2.2'), ('PyInstaller', '6.22.3')):
        metadata = json.loads(read(f'https://pypi.org/pypi/{package}/{version}/json'))
        item = next(item for item in metadata['urls'] if item['packagetype'] == 'sdist')
        sources.append({'file': item['filename'], 'url': item['url'],
                        'sha256': item['digests']['sha256'], 'component': package,
                        'version': version})
    for module in QT_MODULES:
        filename = f'{module}-everywhere-src-{QT_VERSION}.tar.xz'
        url = f'https://download.qt.io/official_releases/qt/6.11/{QT_VERSION}/submodules/{filename}'
        # The Qt release archive publishes its checksum beside each source.
        checksum = read(url + '.sha256').decode().strip().split()[0]
        if not re.fullmatch('[0-9a-fA-F]{64}', checksum):
            raise ValueError(f'Invalid upstream checksum for {filename}')
        sources.append({'file': filename, 'url': url, 'sha256': checksum.lower(),
                        'component': module, 'version': QT_VERSION})

    def fetch(item):
        target = args.destination / item['file']
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
            temporary = target.with_suffix(target.suffix + '.partial')
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(item['url'], timeout=30) as response, temporary.open('wb') as output:
                        while chunk := response.read(1024 * 1024):
                            output.write(chunk)
                    break
                except OSError:
                    if attempt == 2:
                        raise
                    time.sleep(1)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError(f'Source checksum mismatch: {target.name}')
            temporary.replace(target)
        print(f'Verified {target.name} ({target.stat().st_size:,} bytes)', flush=True)
        return item

    with ThreadPoolExecutor(max_workers=4) as pool:
        verified = list(pool.map(fetch, sources))
    (args.destination / 'manifest.json').write_text(
        json.dumps(verified, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
