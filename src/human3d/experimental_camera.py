"""Pinned G3/G4 calibrated and estimated projection model."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Camera:
    """G4 camera convention, with geometry supplied in centimetres."""
    yaw: float
    span: float = 215.
    center_y: float = 0.
    elevation: float = 0.
    distance: float = 650.
    perspective: bool = False
    roll: float = 0.
    dx: float = 0.
    dy: float = 0.

    def __post_init__(self):
        values = (self.yaw, self.span, self.center_y, self.elevation, self.distance, self.roll, self.dx, self.dy)
        if not np.isfinite(values).all() or self.span <= 0 or self.distance <= 0 or type(self.perspective) is not bool:
            raise ValueError("Invalid calibrated camera.")

    def axes(self):
        azimuth, elevation = np.deg2rad([self.yaw, self.elevation])
        right = np.array([np.cos(azimuth), 0, -np.sin(azimuth)])
        towards = np.array([np.sin(azimuth) * np.cos(elevation), np.sin(elevation),
                            np.cos(azimuth) * np.cos(elevation)])
        up = np.cross(towards, right)
        roll = np.deg2rad(self.roll)
        return np.stack((right * np.cos(roll) + up * np.sin(roll),
                         -right * np.sin(roll) + up * np.cos(roll), towards))

    def project(self, vertices, size):
        xyz = (vertices - [0, self.center_y, 0]) @ self.axes().T
        z = self.distance - xyz[:, 2]
        if self.perspective and (z <= 0).any():
            raise ValueError("Calibrated perspective lies inside the candidate body.")
        scale = size / self.span * (self.distance / z if self.perspective else 1.)
        return np.column_stack((size * (.5 + self.dx) + xyz[:, 0] * scale,
                                size * (.5 + self.dy) - xyz[:, 1] * scale))
