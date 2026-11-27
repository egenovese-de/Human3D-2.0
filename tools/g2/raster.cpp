// Pixel-center triangle rasterization. Optional depth and visible triangle index.
#include <algorithm>
#include <cmath>

extern "C" void raster(const float* xy, const int* triangles, int count, int size,
                       unsigned char* mask, float* depth, int* triangle_id, int perspective) {
    for (int i = 0; i < count; ++i) {
        const auto* a = xy + 3 * triangles[3*i];
        const auto* b = xy + 3 * triangles[3*i + 1];
        const auto* c = xy + 3 * triangles[3*i + 2];
        const float ux = b[0]-a[0], uy = b[1]-a[1], vx = c[0]-a[0], vy = c[1]-a[1];
        const float determinant = ux*vy-uy*vx;
        if (std::abs(determinant) < 1e-8f) continue;
        const int x0 = std::max(0, int(std::ceil(std::min({a[0],b[0],c[0]})-.5f)));
        const int x1 = std::min(size-1, int(std::floor(std::max({a[0],b[0],c[0]})-.5f)));
        const int y0 = std::max(0, int(std::ceil(std::min({a[1],b[1],c[1]})-.5f)));
        const int y1 = std::min(size-1, int(std::floor(std::max({a[1],b[1],c[1]})-.5f)));
        for (int y = y0; y <= y1; ++y) {
            for (int x = x0; x <= x1; ++x) {
                const float rx = x+.5f-a[0], ry = y+.5f-a[1];
                const float v = (rx*vy-ry*vx)/determinant;
                const float w = (ux*ry-uy*rx)/determinant;
                const float u = 1-v-w;
                if (u < -1e-6f || v < -1e-6f || w < -1e-6f) continue;
                const int index = y*size+x;
                mask[index] = 1;
                if (!depth) continue;
                const float z = perspective ? 1/(u/a[2]+v/b[2]+w/c[2]) : u*a[2]+v*b[2]+w*c[2];
                if (z < depth[index]) {
                    depth[index] = z;
                    triangle_id[index] = i;
                }
            }
        }
    }
}
