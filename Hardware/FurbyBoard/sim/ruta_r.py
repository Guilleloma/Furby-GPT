"""Resistencia de la ruta de menor resistencia entre dos pads de una red, solo con pistas y vías.

Uso, desde sim/:  python3 -I ruta_r.py ../FurbyBoard.kicad_pcb 3V3 U3.6 U4.2
Cobre: 35 µm en F.Cu/B.Cu y 15,2 µm en las internas (JLC06161H-7628); vías de 0,3 mm con barril de
18 µm y 1,6 mm. No cuenta los rellenos (zonas): para redes que van por relleno da NaN y se estima a mano.
"""
import re, sys, heapq, math
pcb, net, a, b = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
t = open(pcb).read()
RHO = 1.72e-8
TH = {"F.Cu": 35e-6, "B.Cu": 35e-6}  # exteriores 1 oz; interiores 0,5 oz
def th(l): return TH.get(l, 15.2e-6)
nodes = {}; adj = {}
def key(x, y, l): return (round(x, 3), round(y, 3), l)
def edge(u, v, r):
    adj.setdefault(u, []).append((v, r)); adj.setdefault(v, []).append((u, r))
segs = []
for m in re.finditer(r'\n\t\(segment\n(.*?)\n\t\)', t, re.S):
    body = m.group(1)
    if f'(net "{net}")' not in body: continue
    x1, y1 = map(float, re.search(r'\(start ([-\d.]+) ([-\d.]+)\)', body).groups())
    x2, y2 = map(float, re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', body).groups())
    w = float(re.search(r'\(width ([\d.]+)\)', body).group(1)); l = re.search(r'\(layer "([^"]+)"\)', body).group(1)
    L = math.hypot(x2 - x1, y2 - y1)
    r = RHO * L * 1e-3 / (w * 1e-3 * th(l)) if L > 0 else 1e-6
    edge(key(x1, y1, l), key(x2, y2, l), r); segs.append((x1, y1, x2, y2, l, w))
LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
vias = []
for m in re.finditer(r'\n\t\(via\n(.*?)\n\t\)', t, re.S):
    body = m.group(1)
    if f'(net "{net}")' not in body: continue
    x, y = map(float, re.search(r'\(at ([-\d.]+) ([-\d.]+)\)', body).groups())
    d = float(re.search(r'\(drill ([\d.]+)\)', body).group(1))
    rv = RHO * 1.6e-3 / (math.pi * d * 1e-3 * 18e-6)  # barril de 18 um, 1,6 mm
    vias.append((x, y))
    for i in range(len(LAYERS) - 1):
        edge(key(x, y, LAYERS[i]), key(x, y, LAYERS[i + 1]), rv / 5)
# unir puntos que coinciden en la misma capa (extremos de pista sobre vías, tolerancia 0,05)
pts = list(adj.keys())
for i, p in enumerate(pts):
    for q in pts[i + 1:]:
        if p[2] == q[2] and abs(p[0] - q[0]) < 0.06 and abs(p[1] - q[1]) < 0.06 and p != q:
            edge(p, q, 1e-6)
# pads de los extremos
def padpos(ref, num):
    i = t.find(f'"Reference" "{ref}"'); s = t.rfind('(footprint', 0, i)
    fx, fy, *rot = re.search(r'\(at ([-\d.]+) ([-\d.]+) ?([-\d.]*)\)', t[s:s+800]).groups()
    ang = math.radians(float(rot[0])) if rot and rot[0] else 0
    e = t.find('\n\t)', i)
    pm = re.search(r'\(pad "%s" .*?\(at ([-\d.]+) ([-\d.]+)' % re.escape(num), t[s:e], re.S)
    px, py = map(float, pm.groups())
    X = float(fx) + px * math.cos(ang) + py * math.sin(ang); Y = float(fy) - px * math.sin(ang) + py * math.cos(ang)
    return X, Y
def near(X, Y, layers=("F.Cu",), tol=0.8):
    return [p for p in adj if p[2] in layers and math.hypot(p[0] - X, p[1] - Y) < tol]
A = padpos(*a.split('.')); B = padpos(*b.split('.'))
src = near(*A); dst = set(near(*B))
dist = {s: 0 for s in src}; h = [(0, s) for s in src]; best = None
while h:
    d, u = heapq.heappop(h)
    if d > dist.get(u, 1e9): continue
    if u in dst: best = d; break
    for v, r in adj.get(u, []):
        if d + r < dist.get(v, 1e9): dist[v] = d + r; heapq.heappush(h, (d + r, v))
tot = sum(math.hypot(s[2]-s[0], s[3]-s[1]) for s in segs)
print(f"{net}: {len(segs)} pistas ({tot:.1f} mm), {len(vias)} vías; pad {a} {A} -> {b} {B}: R = {best*1e3 if best is not None else float('nan'):.1f} mohm (solo pistas y vías, sin rellenos)")
