import re, shlex, glob
from pathlib import Path

def aliases(path=None):
    root=Path(path or Path.home()/'.ssh'/'config').expanduser()
    seen=set(); found=set()
    def read(p,depth=0):
        if depth>8 or p.resolve() in seen or not p.is_file(): return
        seen.add(p.resolve())
        for line in p.read_text(encoding='utf-8-sig',errors='replace').splitlines():
            try: parts=shlex.split(line,comments=True,posix=False)
            except ValueError: continue
            if not parts: continue
            key=parts.pop(0).lower()
            if key=='host':
                found.update(x.strip('"\'') for x in parts if re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*',x.strip('"\'')))
            elif key=='include':
                for x in parts:
                    q=Path(x.strip('"\'')).expanduser()
                    if not q.is_absolute(): q=root.parent/q
                    for match in glob.glob(str(q)): read(Path(match),depth+1)
    read(root)
    return sorted(found,key=str.lower)
