"""Run the qualified M7 Engine B through the actual project service."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from threading import Event

import numpy as np

from evidence import CONFIG
from human3d.experimental import GeometryEngine
from human3d.experimental_camera import Camera
from human3d.reconstruction import ReconstructionService
from human3d.session import Session

BASELINE = '020fcc793e7417d6927d9e07346678e110ae9ddc'


def engine_b(runtime, rgb, work, *, num_views=None, full=False, estimated=False):
    work.mkdir(parents=True, exist_ok=True)
    folder = work / 'project'
    session = Session(folder, create=not folder.exists())
    yaws = CONFIG['fit_yaw_deg'][:num_views or CONFIG['main_views']]
    photos = [rgb / f'{angle}.png' for angle in yaws]
    session.ingest(photos)
    angles = {sha256(path.read_bytes()).hexdigest(): angle for path, angle in zip(photos, yaws)}
    calibration = work / 'calibration.json'
    if not estimated:
        calibration.write_text(json.dumps({'schema_version': 1, 'views': [
            {'photo_sha256': digest, 'canonical_pose': True, 'independent_scale': True,
             'camera': asdict(Camera(angle, **CONFIG['main_camera_cm']))}
            for digest, angle in angles.items()]}))
    engine = GeometryEngine(runtime)
    service = ReconstructionService(session, {'geometry': engine}, BASELINE)
    request = service.request('geometry', calibration=None if estimated else str(calibration))
    record = service.generate(request, Event(), lambda _: None)
    report = record.metadata
    (work / 'attempt.json').write_text(json.dumps(report, indent=2))
    if report['status'] != 'complete':
        raise ValueError('Engine B attempt failed: ' + json.dumps(report['diagnostics']))
    data = list((folder / 'experimental-canonical').glob('*.npz'))
    if len(data) != 1:
        raise ValueError('Expected exactly one canonical Engine B cache entry')
    with np.load(data[0]) as result:
        vertices = result['vertices'].copy()
        parameters, _, fitting = json.loads(str(result['metadata']))
    angles = {photo.id: angles[photo.digest] for photo in session.store.load().photos.photos}
    return vertices, parameters, fitting, report, session, angles
