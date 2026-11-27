"""Image projection and pixel-centre rasterization in the G1 anatomical frame."""
from dataclasses import asdict, dataclass
import ctypes
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class Camera:
    yaw: float
    span: float = 215.
    center_y: float = 0.
    elevation: float = 0.
    distance: float = 650.
    perspective: bool = False
    roll: float = 0.
    dx: float = 0.
    dy: float = 0.

    def axes(self):
        az, el = np.deg2rad([self.yaw, self.elevation])
        right = np.array([np.cos(az), 0., -np.sin(az)])
        towards = np.array([np.sin(az)*np.cos(el), np.sin(el), np.cos(az)*np.cos(el)])
        up = np.cross(towards, right)
        angle = np.deg2rad(self.roll)
        return np.stack([right*np.cos(angle)+up*np.sin(angle),
                         -right*np.sin(angle)+up*np.cos(angle), towards])

    def project(self, vertices, size):
        xyz = (vertices - [0, self.center_y, 0]) @ self.axes().T
        z = self.distance - xyz[:, 2]
        scale = size / self.span * (self.distance/z if self.perspective else 1.)
        return np.column_stack((size/2+self.dx*size+xyz[:,0]*scale,
                                size/2+self.dy*size-xyz[:,1]*scale, z))

    def manifest(self, size):
        return asdict(self) | {"world_to_camera_axes": self.axes().tolist(),
                               "units": "cm", "raster_px": size,
                               "focal_px": size*self.distance/self.span if self.perspective else None}


class Raster:
    def __init__(self, library):
        self.library = ctypes.CDLL(str(Path(library).resolve()))
        self.call = self.library.raster
        self.call.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        self.call.restype = None

    def draw(self, camera, vertices, triangles, size, channels=False):
        coordinates = np.ascontiguousarray(camera.project(vertices, size), dtype=np.float32)
        faces = np.ascontiguousarray(triangles, dtype=np.int32)
        foreground = np.zeros((size, size), np.uint8)
        depth = np.full((size, size), np.inf, np.float32) if channels else None
        indices = np.full((size, size), -1, np.int32) if channels else None
        self.call(coordinates.ctypes.data, faces.ctypes.data, len(faces), size,
                  foreground.ctypes.data, depth.ctypes.data if channels else None,
                  indices.ctypes.data if channels else None, camera.perspective)
        return (foreground.astype(bool), depth, indices) if channels else foreground.astype(bool)
