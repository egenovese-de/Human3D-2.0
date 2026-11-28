"""Small analytic CPU probes independent of proprietary fixtures."""
import unittest

import numpy as np

from deformation import adjacency, cage, ffd, graph, laplacian


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.vertices = np.array([[x,y,z] for x in (-1.,1.) for y in (-1.,1.) for z in (-1.,1.)])
        self.faces = np.array([[0,1,2],[1,3,2],[4,5,6],[5,7,6],[0,2,4],[2,6,4],
                               [1,3,5],[3,7,5],[0,1,4],[1,5,4],[2,3,6],[3,7,6]])

    def test_ffd_partition_of_unity(self):
        b, l = ffd(self.vertices,(4,4,4))
        np.testing.assert_allclose(b @ np.ones(64),1)
        np.testing.assert_allclose(l @ np.ones(64),0)

    def test_cage_affine_reproduction(self):
        b, l, t = cage(self.vertices)
        np.testing.assert_allclose(b @ t.points,self.vertices)
        np.testing.assert_allclose(l @ np.ones(len(t.points)),0,atol=1e-12)

    def test_graph_and_surface_uniform_translation_null_space(self):
        edge = adjacency(self.vertices,self.faces)
        b,l = graph(self.vertices, edge, np.arange(8),6)
        np.testing.assert_allclose(b @ np.ones(6),1)
        np.testing.assert_allclose(l @ np.ones(6),0)
        np.testing.assert_allclose(laplacian(edge) @ np.ones(8),0,atol=1e-12)


if __name__=='__main__':
    unittest.main()
