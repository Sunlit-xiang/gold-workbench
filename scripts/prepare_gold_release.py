"""Copy an explicit source allowlist into an independent GitHub delivery checkout."""
import argparse
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
DIRECTORIES=('digital_oracle','scripts','tests','web','docs','references','skills','.github')
FILES=('LICENSE','README.md','README.en.md','SKILL.md','AGENTS.md','ARCHITECTURE_SNAPSHOT.md',
       '.gitignore','.gitattributes','requirements-gold.txt','requirements-delivery.txt')
SECRET=re.compile(rb'(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')


def prepare(destination):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    selected=[ROOT/f for f in FILES]
    for directory in DIRECTORIES:
        selected.extend(p for p in (ROOT/directory).rglob('*') if p.is_file()
                        and not any(part in ('node_modules','__pycache__','.env','.git','.deps') for part in p.relative_to(ROOT).parts)
                        and (p.suffix in ('.py','.mjs','.js','.html','.css','.json','.md','.txt','.ps1','.yml','.yaml','.svg')
                             or (directory=='tests' and p.parent.name=='fixtures' and p.suffix=='.csv')))
    for p in selected:
        if SECRET.search(p.read_bytes()):
            raise ValueError('Potential credential detected in '+str(p.relative_to(ROOT)))
    for p in selected:
        target=destination/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    print(f'Prepared {len(selected)} scanned source files; no database, raw archive, .env, node_modules or hosting identity included.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='.delivery/repository');a=p.parse_args();prepare(a.output)
