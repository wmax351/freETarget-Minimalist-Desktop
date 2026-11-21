"""Keep installed dependency notice files with the Mac bundle."""
from importlib import metadata
from pathlib import Path
import json
import shutil

def collect(destination):
    destination=Path(destination)
    if destination.exists():shutil.rmtree(destination)
    destination.mkdir(parents=True)
    inventory=[]
    for dist in metadata.distributions():
        name=dist.metadata.get('Name','unknown').replace('/','_')
        folder=destination/name;folder.mkdir(exist_ok=True)
        (folder/'METADATA.txt').write_text(str(dist.metadata),encoding='utf-8')
        for item in dist.files or []:
            # Test fixtures and debug symbols are not license notices, even when
            # a binary fixture has a name beginning with "copying".
            parts = Path(str(item)).parts
            if any(p.lower() in ('tests', 'test', 'pyobjctest', '__pycache__') or
                   p.lower().endswith('.dsym') for p in parts):continue
            if Path(str(item)).suffix.lower() in ('.so', '.dylib', '.a', '.o', '.pyc'):continue
            if not (Path(str(item)).name.lower().startswith(('license','copying','notice')) or 'licenses' in str(item).lower().split('/')):continue
            source=Path(dist.locate_file(item))
            if not source.is_file():continue
            safe=[x for x in Path(str(item)).parts if x not in ('..','.','/')]
            target=folder.joinpath(*safe);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        inventory.append({'name':name,'version':dist.version})
    (destination/'INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n')

if __name__=='__main__':
    import sys
    collect(sys.argv[1])
