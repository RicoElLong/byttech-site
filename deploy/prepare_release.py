"""Assemble the frontend and separately reviewed callback API without publishing."""
import argparse
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from build_pages import build


def prepare_release(destination: Path, backend: Path, production=False):
    destination=destination.resolve(); backend=backend.resolve()
    root=Path(__file__).resolve().parents[1]
    if destination.exists() or destination.is_relative_to(root) or destination.is_relative_to(backend):
        raise ValueError('Use a new release directory outside both repositories.')
    required=('web_api.py','web_leads.py','requirements-web.txt')
    if any(not (backend/name).is_file() for name in required):
        raise ValueError('Reviewed callback API checkout is required.')
    if "@app.post('/api/requests')" not in (backend/'web_api.py').read_text():
        raise ValueError('Backend lacks the reviewed /api/requests compatibility route.')
    with TemporaryDirectory(prefix='.byttech-',dir=destination.parent) as temp:
        release=Path(temp)/'release';release.mkdir()
        build(release/'site',production=production)
        for name in required:
            shutil.copy2(backend/name,release/name)
        shutil.copy2(root/'deploy/nginx.conf.example',release/'nginx.conf.example')
        shutil.copy2(root/'deploy/analytics_server.py',release/'analytics_server.py')
        release.rename(destination)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--backend-dir',type=Path,required=True)
    parser.add_argument('--production',action='store_true')
    args=parser.parse_args()
    prepare_release(args.destination,args.backend_dir,args.production)
