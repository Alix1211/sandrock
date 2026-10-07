# 샌드락 새 마을 (루시에라의 마을) — build.py에서 불러 씀
# 원래 큰 마을(map 'town')은 그대로 두고, 이 마을은 별도 맵 'sand'로 들어간다(케인 확정 2026-10-07: 두 세계를 섞되 아무것도 버리지 않음).
# 건물·NPC 그림: assets/sandrock (tools/sandrock_slice.py 결과). 배치 뼈대는 GPT가 잡은 23채 자리를 이어받음.
import os, random, numpy as np
from PIL import Image
from scipy import ndimage as nd

SAND_W, SAND_H = 72, 50

# 길·광장 (칸 좌표 사각형)
PLAZA = (25.0, 17.0, 47.0, 27.8)
COBBLE = [
    PLAZA,
    (34.0, 8.5, 38.5, 30.0),      # 시청-광장 세로축
    (10.0, 19.0, 63.5, 23.7),     # 상업 메인거리
    (14.0, 27.0, 58.5, 30.6),     # 남쪽 상업거리
    (36.8, 27.0, 41.2, 50.5),     # 연못 오른쪽-정문 큰길
    (48.0, 34.0, 64.0, 37.0),     # 주거/작업장 연결
]
DIRT = [
    (8.0, 11.5, 63.5, 15.5),      # 북부 행정/연구 지구
    (7.0, 22.5, 12.0, 42.5),      # 서쪽 자원/창고 지구
    (58.0, 20.5, 66.0, 45.5),     # 동쪽 생산 지구
    (10.0, 33.0, 28.0, 36.5),     # 서남 주거/목공
    (47.0, 39.0, 65.0, 45.5),     # 공방/주거 지구
    (20.5, 41.0, 38.5, 45.0),     # 경비대-정문 연결
]
POND = (35.0, 34.4, 5.8, 2.6)     # 중심x, 중심y, 반지름x, 반지름y

# 걸어 다닐 수 있는 마을 영역(칸). 밖은 막고 어둡게 — 필드와 같은 방식(칸 단위 어둠 + 15px 페더).
TOWN_AREA = (6, 10, 66, 50)       # x0, y0, x1, y1 (칸, x1·y1 미포함)
TOWN_CORNER = 3                   # 모서리 둥글림(칸)
DARK = (18, 62, 24, 0.49)         # 필드 봄 테마와 같은 어둠 색·진하기
FEATHER = 15                      # 게임 픽셀 기준 페더(필드와 동일)


def walkable(x, y):
    x0, y0, x1, y1 = TOWN_AREA
    if not (x0 <= x < x1 and y0 <= y < y1): return False
    r = TOWN_CORNER
    cx = min(max(x + 0.5, x0 + r), x1 - r); cy = min(max(y + 0.5, y0 + r), y1 - r)
    return (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r


def edge_solids(TS):
    out = []
    for y in range(SAND_H):
        x = 0
        while x < SAND_W:
            if walkable(x, y): x += 1; continue
            s = x
            while x < SAND_W and not walkable(x, y): x += 1
            out.append(dict(x0=s * TS, x1=x * TS, y0=y * TS, y1=(y + 1) * TS))
    return out

# 건물: assets/sandrock/buildings/<key>.png, 중심x, 바닥y, 폭(칸), 문 x 보정(폭 비율)
BLDS = [
    ('city_hall',       36.0, 12.8, 6.6, 0.00),
    ('research_center', 24.0, 13.4, 5.4, 0.00),
    ('community_hall',  47.5, 13.4, 5.4, 0.00),
    ('mine_office',     13.0, 13.8, 5.2, 0.00),
    ('ruin_office',     58.0, 13.8, 5.2, 0.00),
    ('guild',           36.0, 18.6, 5.6, 0.00),
    ('post_office',     20.5, 21.0, 4.6, 0.00),
    ('general_store',   27.0, 21.0, 4.6, 0.00),
    ('material_shop',   45.0, 21.0, 4.6, 0.00),
    ('clothing',        51.5, 21.0, 4.6, 0.00),
    ('blacksmith',      58.0, 22.0, 5.2, 0.00),
    ('recycling',        9.5, 24.7, 5.0, 0.00),
    ('restaurant',      28.0, 30.0, 5.0, 0.00),
    ('inn',             36.0, 30.0, 5.4, 0.00),
    ('pharmacy',        44.0, 30.0, 4.6, 0.00),
    ('trading_post',    51.0, 30.0, 5.0, 0.00),
    ('carpentry',       18.0, 35.0, 5.2, 0.00),
    ('warehouse',        9.5, 35.0, 5.2, 0.00),
    ('mansion',         61.0, 35.2, 5.8, 0.00),
    ('residence',       53.0, 40.5, 4.8, 0.00),
    ('abandoned',       10.5, 42.3, 5.0, 0.00),
    ('guard_hq',        26.0, 43.5, 6.0, 0.00),
    ('workshop',        61.0, 44.2, 5.6, 0.00),
]
GATE = (36.0, 50.0, 7.0)   # 정문(성 밖으로) — 원래 마을과 같은 성문 그림

# 소품(원래 마을과 같은 마을 소품 그림): 경로, 이름, x, 바닥y, 폭(칸), 충돌(폭 비율, 깊이 칸)
TP = 'town_props/'
PROPS = [
    (TP + 'fountain', None, 36.0, 25.2, 4.2, (0.86, 1.3)),
    (TP + 'signpost', '이정표', 39.8, 28.2, 1.2, (0.4, 0.3)),
    (TP + 'well', '우물', 49.0, 39.0, 2.4, (0.8, 0.9)),
    (TP + 'stall_blue', '노점', 23.5, 25.5, 3.0, (0.85, 0.9)),
    (TP + 'stall_red', '노점', 48.5, 25.5, 3.0, (0.85, 0.9)),
    (TP + 'bench_iron', None, 31.0, 26.3, 2.0, (0.9, 0.5)),
    (TP + 'bench_iron', None, 41.0, 26.3, 2.0, (0.9, 0.5)),
    (TP + 'lamp_iron', None, 27.0, 24.2, 1.0, (0.5, 0.3)),
    (TP + 'lamp_iron', None, 45.0, 24.2, 1.0, (0.5, 0.3)),
    (TP + 'lamp_iron', None, 31.0, 18.0, 1.0, (0.5, 0.3)),
    (TP + 'lamp_iron', None, 41.0, 18.0, 1.0, (0.5, 0.3)),
    (TP + 'lamp_wood', None, 38.8, 31.0, 1.1, (0.4, 0.3)),
    (TP + 'lamp_wood', None, 40.0, 39.0, 1.1, (0.4, 0.3)),
    (TP + 'woodpile', None, 21.8, 38.6, 1.9, (0.9, 0.5)),
    (TP + 'cart', None, 13.0, 38.4, 2.4, (0.85, 0.6)),
    (TP + 'barrel_bucket', None, 55.0, 25.6, 1.4, (0.8, 0.4)),
    (TP + 'tree_big', None, 17.0, 17.2, 4.0, (0.16, 0.3)),
    (TP + 'tree_blossom', None, 30.5, 16.2, 3.2, (0.16, 0.3)),
    (TP + 'tree_big', None, 54.5, 17.0, 4.0, (0.16, 0.3)),
    (TP + 'tree_small', None, 42.0, 16.4, 3.0, (0.16, 0.3)),
    (TP + 'tree_big', None, 29.0, 38.0, 4.0, (0.16, 0.3)),
    (TP + 'tree_small', None, 44.5, 38.0, 3.0, (0.16, 0.3)),
    (TP + 'tree_blossom', None, 46.5, 46.0, 3.2, (0.16, 0.3)),
    (TP + 'tree_big', None, 68.0, 30.0, 4.0, (0.16, 0.3)),
    (TP + 'tree_small', None, 4.0, 30.0, 3.0, (0.16, 0.3)),
    (TP + 'tree_big', None, 4.0, 46.0, 4.0, (0.16, 0.3)),
    (TP + 'tree_big', None, 68.0, 47.0, 4.0, (0.16, 0.3)),
]

# NPC: 건물 앞 고정(경비대만 둘). 이름은 아직 미정 → 건물 이름만 보여 준다(GPT 임시 이름은 쓰지 않음).
SPAWN = (39.0, 42.0)       # 첫 시작·성 밖에서 돌아올 때 위치(정문 안쪽 큰길)


def gen_ground(R, px, seed, cache):
    if os.path.exists(cache): return Image.open(cache).convert('RGB')
    mw, mh = SAND_W, SAND_H
    rng = np.random.RandomState(seed); random.seed(seed)
    W, H = mw * px, mh * px
    def tex(n):
        t = np.asarray(Image.open(R + f'tiles/spring/{n}.png').convert('RGB').resize((px, px), Image.LANCZOS))
        return np.tile(t, (mh, mw, 1)).astype(np.float32)
    grass, flower, cobble, dirt, sand, water = (tex(n) for n in ('grass', 'grass_flower', 'path', 'dirt', 'sand', 'water'))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) / px
    def noise(scale, amp):
        n = rng.rand(H // 8 + 2, W // 8 + 2).astype(np.float32); n = nd.gaussian_filter(n, scale / 8)
        n = (n - n.mean()) / (n.std() + 1e-6)
        return np.asarray(Image.fromarray(n).resize((W, H), Image.BILINEAR)) * amp
    N1, N2 = noise(24, 0.18), noise(60, 0.5)
    def union(rects):
        s = np.full((H, W), 1e9, np.float32)
        for x0, y0, x1, y1 in rects:
            dx = np.maximum(x0 - xx, xx - x1); dy = np.maximum(y0 - yy, yy - y1)
            s = np.minimum(s, np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0))
        return s
    img = grass.copy()
    fm = np.zeros((H, W), np.float32)
    for _ in range(16):
        cx, cy, r = random.uniform(1, mw - 1), random.uniform(1, mh - 1), random.uniform(1.0, 2.2)
        fm = np.maximum(fm, np.clip(1.4 - np.hypot(xx - cx, yy - cy) / r + N2 * 0.6, 0, 1))
    img = img * (1 - fm[..., None]) + flower * fm[..., None]
    sd = union(DIRT)
    md = np.clip(0.5 - (sd + N1) / 0.25, 0, 1)[..., None]
    shade = np.clip(0.5 - (sd + N1 - 0.12) / 0.25, 0, 1)[..., None] - md
    img = img * (1 - 0.25 * np.clip(shade, 0, 1)); img = img * (1 - md) + dirt * md
    sc = union(COBBLE)
    mc = np.clip(0.5 - (sc + N1 * 0.25) / 0.06, 0, 1)[..., None]
    rim = np.clip(0.5 - (sc - 0.10) / 0.10, 0, 1)[..., None] - mc
    img = img * (1 - 0.35 * np.clip(rim, 0, 1)); img = img * (1 - mc) + cobble * mc
    pcx, pcy, prx, pry = POND
    pd = np.hypot((xx - pcx) / prx, (yy - pcy) / pry) - 1 + N2 * 0.06
    ms = np.clip(0.5 - (pd - 0.26) / 0.10, 0, 1)[..., None]
    mwt = np.clip(0.5 - pd / 0.06, 0, 1)[..., None]
    img = img * (1 - ms) + sand * ms; img = img * (1 - mwt) + water * mwt
    # 못 가는 곳: 칸 단위로 어둡게 칠한 뒤 페더(필드 field_dungeon.js와 같은 방식)
    shade = np.zeros((mh, mw), np.float32)
    for y in range(mh):
        for x in range(mw):
            if not walkable(x, y): shade[y, x] = 1
    shade = np.kron(shade, np.ones((px, px), np.float32))
    shade = nd.gaussian_filter(shade, FEATHER * px / 48)
    a = DARK[3] * shade[..., None]
    img = img * (1 - a) + np.array(DARK[:3], np.float32) * a
    g = Image.fromarray(img.clip(0, 255).astype(np.uint8)); g.save(cache); return g


def pond_solids(TS):
    """연못: 타원을 가로 띠 여러 개로 막는다."""
    cx, cy, rx, ry = POND
    out = []
    for i in range(8):
        t0, t1 = -1 + i / 4, -1 + (i + 1) / 4
        tm = (t0 + t1) / 2
        half = rx * 0.92 * (1 - tm * tm) ** 0.5
        out.append(dict(x0=(cx - half) * TS, x1=(cx + half) * TS, y0=(cy + t0 * ry * 0.92) * TS, y1=(cy + t1 * ry * 0.92) * TS))
    return out
