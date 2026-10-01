"""Build-only HTML documentation, sanitized source tree and release payload."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys
import zipfile
import markdown

project, stage = (Path(value).resolve() for value in sys.argv[1:3])
if not (project / 'app/Codex-Glass/Codex-Glass.exe').is_file():
    raise SystemExit('Build the application first')
source_stage = stage / 'source'
source_stage.mkdir(parents=True, exist_ok=True)
for path in (project / 'source').rglob('*'):
    if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
        target = source_stage / path.relative_to(project / 'source')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

style = '''body{max-width:820px;margin:50px auto;padding:0 24px;font:16px/1.8 "Segoe UI",sans-serif;color:#22312d;background:#f8faf9}h1,h2,h3{line-height:1.4}h2{margin-top:2em}a{color:#32796a}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #dce5e0;padding:8px 12px;text-align:left}pre{background:#eaf0ec;padding:18px;border-radius:12px;overflow:auto}code{font-family:Consolas,monospace}blockquote{margin:0;padding:10px 20px;border-left:3px solid #8bbba7}'''
for source, output in [('README.md','使用说明.html'), ('DEVELOPMENT.md','开发说明.html'),
                       ('SHARING.md','分享说明.html'), ('THIRD-PARTY.md','第三方许可.html')]:
    content = (project / source).read_text(encoding='utf-8')
    for before, after in [('README.md','使用说明.html'),('DEVELOPMENT.md','开发说明.html'),
                          ('SHARING.md','分享说明.html'),('THIRD-PARTY.md','第三方许可.html')]:
        content = content.replace(f']({before})', f']({after})')
    body = markdown.markdown(content, extensions=['tables','fenced_code'])
    (stage / output).write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(output[:-5]) + ' · Codex-Glass</title><style>' + style + '</style><body>' + body + '</body></html>', encoding='utf-8')

with zipfile.ZipFile(stage / 'Codex-Glass-3.1.1-Source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for folder in ('source', 'third-party-licenses'):
        root = source_stage if folder == 'source' else project / folder
        for path in sorted(root.rglob('*')):
            if path.is_file():
                archive.write(path, 'Codex-Glass/' + folder + '/' + path.relative_to(root).as_posix())
    for name in ('LICENSE','NOTICE.md','README.md','DEVELOPMENT.md','SHARING.md','THIRD-PARTY.md'):
        archive.write(project / name, 'Codex-Glass/' + name)
    for path in sorted(project.glob('preview-*.png')):
        archive.write(path, 'Codex-Glass/' + path.name)
    archive.write(project / 'design-qa.md', 'Codex-Glass/design-qa.md')
    archive.write(project / 'reference-comparison.png', 'Codex-Glass/reference-comparison.png')

manifest = []
for root in (project / 'app/Codex-Glass', source_stage, project / 'dependency-sources'):
    for path in sorted(root.rglob('*')):
        if path.is_file():
            manifest.append({'file':root.name + '/' + path.relative_to(root).as_posix(),
                             'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(stage / 'payload-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Staged {len(manifest)} files and offline documentation')
