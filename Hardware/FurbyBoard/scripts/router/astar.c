/* A* en rejilla de varias capas para el rutador de la FurbyBoard.
 *
 * Celdas (capa, y, x). En cada capa se avanza en 8 direcciones (coste 10 recto,
 * 14 en diagonal); entre capas solo se cambia donde cabe una vía (via_ok), con
 * coste coste_via. Varias fuentes y un conjunto de celdas objetivo. La búsqueda
 * se limita a una ventana [x0,x1) × [y0,y1). La heurística es la distancia
 * octil a la caja de los objetivos (admisible).
 *
 * Se compila al vuelo (rutar.py) con: cc -O2 -shared -fPIC -o astar.so astar.c
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int32_t f; int32_t idx; } nodo;

static nodo *heap = NULL;
static int heap_n = 0, heap_cap = 0;

static void push(int32_t f, int32_t idx) {
    if (heap_n == heap_cap) {
        heap_cap = heap_cap ? heap_cap * 2 : 1 << 16;
        heap = (nodo *)realloc(heap, sizeof(nodo) * heap_cap);
    }
    int i = heap_n++;
    while (i > 0) {
        int p = (i - 1) / 2;
        if (heap[p].f <= f) break;
        heap[i] = heap[p];
        i = p;
    }
    heap[i].f = f;
    heap[i].idx = idx;
}

static nodo pop(void) {
    nodo top = heap[0], last = heap[--heap_n];
    int i = 0;
    for (;;) {
        int c = 2 * i + 1;
        if (c >= heap_n) break;
        if (c + 1 < heap_n && heap[c + 1].f < heap[c].f) c++;
        if (heap[c].f >= last.f) break;
        heap[i] = heap[c];
        i = c;
    }
    heap[i] = last;
    return top;
}

static int32_t octil(int dx, int dy) {
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    int mn = dx < dy ? dx : dy, mx = dx < dy ? dy : dx;
    return 14 * mn + 10 * (mx - mn);
}

/* coste_capa: coste extra por paso en cada capa (para preferir unas sobre otras).
 * camino: salida, triples (capa, y, x) del objetivo a la fuente. Devuelve su
 * longitud en celdas, o -1 si no hay camino. */
int astar(int W, int H, int NL, const uint8_t *libre, const uint8_t *via_ok, const uint8_t *objetivo,
          const int32_t *fuentes, int nf, int coste_via, const int32_t *coste_capa,
          int x0, int y0, int x1, int y1, int tx0, int ty0, int tx1, int ty1,
          int32_t *camino, int max_len) {
    const int N = NL * H * W;
    int32_t *g = (int32_t *)malloc(sizeof(int32_t) * N);
    int32_t *de = (int32_t *)malloc(sizeof(int32_t) * N);
    if (!g || !de) return -2;
    for (int i = 0; i < N; i++) g[i] = INT32_MAX;
    heap_n = 0;
    static const int DX[8] = {1, -1, 0, 0, 1, 1, -1, -1};
    static const int DY[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    static const int DC[8] = {10, 10, 10, 10, 14, 14, 14, 14};
    for (int k = 0; k < nf; k++) {
        int l = fuentes[3 * k], y = fuentes[3 * k + 1], x = fuentes[3 * k + 2];
        int idx = (l * H + y) * W + x;
        g[idx] = 0;
        de[idx] = -1;
        int hx = x < tx0 ? tx0 - x : (x > tx1 ? x - tx1 : 0);
        int hy = y < ty0 ? ty0 - y : (y > ty1 ? y - ty1 : 0);
        push(octil(hx, hy), idx);
    }
    int fin = -1;
    while (heap_n) {
        nodo n = pop();
        int idx = n.idx;
        int l = idx / (H * W), r = idx % (H * W), y = r / W, x = r % W;
        int hx = x < tx0 ? tx0 - x : (x > tx1 ? x - tx1 : 0);
        int hy = y < ty0 ? ty0 - y : (y > ty1 ? y - ty1 : 0);
        if (n.f > g[idx] + octil(hx, hy)) continue;
        if (objetivo[idx]) { fin = idx; break; }
        for (int d = 0; d < 8; d++) {
            int nx = x + DX[d], ny = y + DY[d];
            if (nx < x0 || nx >= x1 || ny < y0 || ny >= y1) continue;
            int ni = (l * H + ny) * W + nx;
            if (!libre[ni]) continue;
            if (d >= 4) {   /* en diagonal, las dos celdas rectas también libres */
                if (!libre[(l * H + y) * W + nx] || !libre[(l * H + ny) * W + x]) continue;
            }
            int32_t ng = g[idx] + DC[d] + coste_capa[l];
            if (ng < g[ni]) {
                g[ni] = ng;
                de[ni] = idx;
                int hx2 = nx < tx0 ? tx0 - nx : (nx > tx1 ? nx - tx1 : 0);
                int hy2 = ny < ty0 ? ty0 - ny : (ny > ty1 ? ny - ty1 : 0);
                push(ng + octil(hx2, hy2), ni);
            }
        }
        if (via_ok[y * W + x]) {
            for (int nl = 0; nl < NL; nl++) {
                if (nl == l) continue;
                int ni = (nl * H + y) * W + x;
                if (!libre[ni]) continue;
                int32_t ng = g[idx] + coste_via;
                if (ng < g[ni]) {
                    g[ni] = ng;
                    de[ni] = idx;
                    push(ng + octil(hx, hy), ni);
                }
            }
        }
    }
    int len = -1;
    if (fin >= 0) {
        len = 0;
        for (int i = fin; i >= 0 && len < max_len; i = de[i]) {
            int l = i / (H * W), r = i % (H * W);
            camino[3 * len] = l;
            camino[3 * len + 1] = r / W;
            camino[3 * len + 2] = r % W;
            len++;
        }
    }
    free(g);
    free(de);
    return len;
}

/* Distancia euclídea (en celdas) a la celda marcada más cercana: transformada
 * exacta de Felzenszwalb y Huttenlocher, en dos pasadas 1D. Salida en float. */
static void edt1d(const double *f, int n, double *d, int *v, double *z) {
    int k = 0;
    v[0] = 0;
    z[0] = -1e30;
    z[1] = 1e30;
    for (int q = 1; q < n; q++) {
        double s = ((f[q] + (double)q * q) - (f[v[k]] + (double)v[k] * v[k])) / (2.0 * q - 2.0 * v[k]);
        while (s <= z[k]) {
            k--;
            s = ((f[q] + (double)q * q) - (f[v[k]] + (double)v[k] * v[k])) / (2.0 * q - 2.0 * v[k]);
        }
        k++;
        v[k] = q;
        z[k] = s;
        z[k + 1] = 1e30;
    }
    k = 0;
    for (int q = 0; q < n; q++) {
        while (z[k + 1] < q) k++;
        double dq = (double)(q - v[k]);
        d[q] = dq * dq + f[v[k]];
    }
}

void edt(int W, int H, const uint8_t *marca, float *salida) {
    int n = W > H ? W : H;
    double *f = (double *)malloc(sizeof(double) * n), *d = (double *)malloc(sizeof(double) * n);
    double *z = (double *)malloc(sizeof(double) * (n + 1));
    double *tmp = (double *)malloc(sizeof(double) * (size_t)W * H);
    int *v = (int *)malloc(sizeof(int) * n);
    const double INF = 1e12;
    for (int x = 0; x < W; x++) {
        for (int y = 0; y < H; y++) f[y] = marca[y * W + x] ? 0.0 : INF;
        edt1d(f, H, d, v, z);
        for (int y = 0; y < H; y++) tmp[y * W + x] = d[y];
    }
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) f[x] = tmp[y * W + x];
        edt1d(f, W, d, v, z);
        for (int x = 0; x < W; x++) salida[y * W + x] = (float)d[x];
    }
    free(f); free(d); free(z); free(v); free(tmp);
}
