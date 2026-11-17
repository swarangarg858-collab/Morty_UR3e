#!/usr/bin/env python3
"""Generate one hollow frustum mesh for the combined controller stand."""

from math import cos, pi, sin
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "meshes" / "controller_stand_frustum_d60_to_d30_h45_hole12.stl"
SEGMENTS = 64
Z_BOTTOM, Z_TOP = -0.225, 0.225
R_BOTTOM, R_TOP, R_HOLE = 0.30, 0.15, 0.06


def ring(radius, z):
    return [(radius * cos(2 * pi * i / SEGMENTS), radius * sin(2 * pi * i / SEGMENTS), z)
            for i in range(SEGMENTS)]


def normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1],
         u[2] * v[0] - u[0] * v[2],
         u[0] * v[1] - u[1] * v[0])
    length = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    return tuple(component / length for component in n)


def facet(a, b, c):
    n = normal(a, b, c)
    lines = [f"      facet normal {n[0]:.8g} {n[1]:.8g} {n[2]:.8g}", "        outer loop"]
    lines.extend(f"          vertex {p[0]:.8g} {p[1]:.8g} {p[2]:.8g}" for p in (a, b, c))
    lines.extend(["        endloop", "      endfacet"])
    return lines


ob, ot = ring(R_BOTTOM, Z_BOTTOM), ring(R_TOP, Z_TOP)
ib, it = ring(R_HOLE, Z_BOTTOM), ring(R_HOLE, Z_TOP)
facets = []
for i in range(SEGMENTS):
    j = (i + 1) % SEGMENTS
    # Outer tapered wall, outward-facing.
    facets += [facet(ob[i], ob[j], ot[j]), facet(ob[i], ot[j], ot[i])]
    # Bore wall, inward-facing, so the square support post passes through it.
    facets += [facet(ib[i], it[j], ib[j]), facet(ib[i], it[i], it[j])]
    # Top annulus (+Z) and bottom annulus (-Z).
    facets += [facet(ot[i], ot[j], it[j]), facet(ot[i], it[j], it[i])]
    facets += [facet(ob[i], ib[j], ob[j]), facet(ob[i], ib[i], ib[j])]

OUT.write_text("\n".join(["solid controller_stand_frustum_d60_to_d30_h45_hole12", *sum(facets, []), "endsolid controller_stand_frustum_d60_to_d30_h45_hole12", ""]), encoding="ascii")
print(f"Wrote {OUT} ({len(facets)} triangles)")
