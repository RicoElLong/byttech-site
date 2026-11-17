"""Validate an editor export, then update public source JSON. Does not publish."""
import argparse
import json
from pathlib import Path
from content_model import load_bundle

ROOT=Path(__file__).resolve().parents[1]


def apply(path):
    bundle=load_bundle(ROOT,path)
    # Validation completes before any source file is touched.
    for key in ('site','articles','reviews'):
        target=ROOT/'content'/f'{key}.json'
        temporary=target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(bundle[key],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temporary.replace(target)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path)
    args=parser.parse_args()
    apply(args.file)
    print('Public content updated. Review git diff, build and test before publishing.')
