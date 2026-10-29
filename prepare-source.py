#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fetch a pinned kernel, apply the port, and verify every exported source file."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tarfile,urllib.request

def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def main():
 repo=Path(__file__).resolve().parent
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--archive',type=Path,help='Use an existing upstream archive; its checksum is still verified')
 p.add_argument('--output',type=Path,default=repo/'kernel-work')
 a=p.parse_args();manifest=json.loads((repo/'source-manifest.json').read_text())
 output=a.output.resolve();output.mkdir(parents=True,exist_ok=True)
 commit=manifest['base_commit'];tree=output/('linux-'+commit)
 if tree.exists():p.error(str(tree)+' already exists; choose a new output directory (nothing was deleted)')
 archive=a.archive.resolve() if a.archive else output/('linux-'+commit+'.tar.gz')
 if not archive.exists():
  if a.archive:p.error('Specified archive does not exist')
  url='https://github.com/torvalds/linux/archive/'+commit+'.tar.gz'
  with urllib.request.urlopen(url,timeout=120) as response,archive.open('xb') as target:
   while block:=response.read(1024*1024):target.write(block)
 if sha256(archive)!=manifest['base_archive_sha256']:p.error('Upstream archive SHA256 mismatch')
 with tarfile.open(archive) as tar:
  for member in tar:
   if member.name.split('/')[0]!='linux-'+commit:p.error('Unexpected archive root')
  tar.extractall(output,filter='data')
 for name in (repo/'patches/series').read_text().splitlines():
  if not name.strip() or name.startswith('#'):continue
  patch=(repo/'patches'/name).resolve()
  if patch.parent!=repo/'patches':p.error('Invalid patch path')
  # git apply discovers the enclosing port repository when the default output
  # is under this checkout, then silently skips paths outside its prefix.
  # patch always interprets paths relative to this prepared kernel tree.
  command=['patch','--batch','--forward','--fuzz=0','-p1','-i',str(patch)]
  subprocess.run(command+['--dry-run'],cwd=tree,check=True,stdout=subprocess.DEVNULL)
  subprocess.run(command,cwd=tree,check=True,stdout=subprocess.DEVNULL)
 for relative,expected in manifest['portable_source_sha256'].items():
  source=(tree/relative).resolve()
  if not source.is_relative_to(tree) or sha256(source)!=expected:raise RuntimeError('Source mismatch: '+relative)
 print('PASS: pinned upstream archive and',len(manifest['portable_source_sha256']),'patched source files verified')
 print(tree)

if __name__=='__main__':main()
