# 샌드락 새 마을 (루시에라의 마을, 맵 'sand') — build.py에서 불러 씀
# 원래 큰 마을('town')과 섞지 않는 독립 파일(나중에 GQS로 옮겨 붙이기 쉽게).
# 구조(케인 확정 2026-10-07, docs/sand_town_plan_v1.png):
#   남쪽 정문 → 입구 광장(가게) → 큰길 → 중앙 분수 광장(시청) / 서쪽 생산 구역 / 동쪽 주거 구역
#   길만 걸을 수 있고, 길 북쪽 건물 터는 밝은 풀, 나머지는 못 가는 곳(필드식 어둠 + 15px 페더).
#   건물 그림은 모두 정면(남쪽)이 문이므로 반드시 길의 북쪽 면에 세운다(바닥선 = 길 윗변).
import os, random, numpy as np
from PIL import Image
from scipy import ndimage as nd

SAND_W, SAND_H = 64, 52

# ---- 길(칸 사각형 x0, y0, x1, y1) ----
ROADS = [
    (13.5, 34.6, 50.5, 42.0),   # 입구 광장
    (29.5, 41.5, 34.5, 52.0),   # 정문 길
    (29.5, 21.0, 34.5, 35.0),   # 큰길(입구 광장 ↔ 분수 광장)
    (23.0, 12.8, 41.0, 21.8),   # 중앙 분수 광장
    (1.5, 25.8, 62.5, 28.6),    # 가운데 동서 거리
    (1.5, 19.0, 23.5, 21.6),    # 서쪽 거리(생산 구역)
    (40.5, 19.0, 62.5, 21.6),   # 동쪽 거리(주거 구역)
    (1.5, 15.5, 4.2, 28.6),     # 서쪽 골목(유적 1 입구)
    (59.8, 15.5, 62.5, 28.6),   # 동쪽 골목(유적 2 입구)
]
PLAZAS = [ROADS[0], ROADS[3]]   # 광장은 돌바닥, 나머지 거리는 흙길

# ---- 건물: 키(assets/sandrock/buildings 또는 houses), 중심x, 바닥y, 폭(칸), 좌우반전 ----
# 바닥y = 앞 길의 윗변(+0.2). 문은 그림 아래 가운데.
B_PLAZA_N = 34.8   # 입구 광장 북쪽 면
B_MID = 26.0       # 가운데 거리 북쪽 면
B_SIDE = 19.2      # 서·동쪽 거리 북쪽 면
B_CENTER = 13.0    # 분수 광장 북쪽 면
BLDS = [
    # 중앙 분수 광장 북쪽: 연구센터 · 시청 · 마을회관
    ('research_center', 25.9, B_CENTER, 5.2, False),
    ('city_hall',       32.0, B_CENTER, 6.4, False),
    ('community_hall',  38.1, B_CENTER, 5.2, False),
    # 서쪽 거리(생산): 광산 관리소 · 창고 · 재활용소 · 목공소
    ('mine_office',      7.2, B_SIDE, 4.6, False),
    ('warehouse',       11.9, B_SIDE, 4.6, False),
    ('recycling',       16.6, B_SIDE, 4.6, False),
    ('carpentry',       21.0, B_SIDE, 4.2, False),
    # 동쪽 거리(주거): 길드 · 집 · 유적 관리소 · 민가
    ('guild',           44.0, B_SIDE, 5.0, False),
    ('house_03',        48.8, B_SIDE, 4.2, False),
    ('ruin_office',     53.4, B_SIDE, 4.6, False),
    ('residence',       57.8, B_SIDE, 4.0, False),
    # 가운데 거리 서쪽: 집 · 대장간 · 집 · 의류점 · 약방
    ('house_01',         6.6, B_MID, 4.0, False),
    ('blacksmith',      11.4, B_MID, 5.0, False),
    ('house_07',        16.3, B_MID, 4.2, True),
    ('clothing',        20.9, B_MID, 4.4, False),
    ('pharmacy',        25.9, B_MID, 4.4, False),
    # 가운데 거리 동쪽: 교역소 · 집 · 집 · 저택 · 폐건물
    ('trading_post',    38.1, B_MID, 4.6, False),
    ('house_05',        42.7, B_MID, 4.2, False),
    ('house_09',        47.0, B_MID, 4.0, True),
    ('mansion',         52.4, B_MID, 5.6, False),
    ('abandoned',       57.6, B_MID, 4.4, False),
    # 입구 광장 북쪽: 경비대 · 여관 · 잡화점 | 재료상 · 식당 · 우체국
    ('guard_hq',        16.6, B_PLAZA_N, 5.0, False),
    ('inn',             21.6, B_PLAZA_N, 4.8, False),
    ('general_store',   26.3, B_PLAZA_N, 4.4, False),
    ('material_shop',   37.7, B_PLAZA_N, 4.4, False),
    ('restaurant',      42.4, B_PLAZA_N, 4.8, False),
    ('post_office',     47.3, B_PLAZA_N, 4.6, False),
    # 입구 광장 양 끝 남의 집(광장 남쪽 너머 동네)
    ('house_02',        12.0, B_PLAZA_N + 0.0, 0.0, False),  # 자리 표시용(폭 0 = 사용 안 함)
]
BLDS = [b for b in BLDS if b[3] > 0]
GATE = (32.0, 52.0, 6.6)   # 정문(성 밖으로) — 원래 마을과 같은 성문 그림

# 소품: 경로, 이름, x, 바닥y, 폭(칸), 충돌(폭 비율, 깊이 칸)
TP = 'town_props/'
FP = 'field_props/spring/'
PROPS = [
    (TP + 'fountain', None, 32.0, 18.6, 4.2, (0.86, 1.3)),
    (TP + 'bench_iron', None, 26.4, 20.6, 2.0, (0.9, 0.5)),
    (TP + 'bench_iron', None, 37.6, 20.6, 2.0, (0.9, 0.5)),
    (TP + 'lamp_iron', None, 28.6, 16.2, 1.0, (0.5, 0.3)),
    (TP + 'lamp_iron', None, 35.4, 16.2, 1.0, (0.5, 0.3)),
    (TP + 'signpost', '이정표', 35.6, 40.2, 1.2, (0.4, 0.3)),
    (TP + 'stall_blue', '노점', 19.0, 39.8, 3.0, (0.85, 0.9)),
    (TP + 'stall_red', '노점', 45.0, 39.8, 3.0, (0.85, 0.9)),
    (TP + 'lamp_iron', None, 28.6, 38.0, 1.0, (0.5, 0.3)),
    (TP + 'lamp_iron', None, 35.4, 38.0, 1.0, (0.5, 0.3)),
    (TP + 'barrel_bucket', None, 14.6, 40.6, 1.4, (0.8, 0.4)),
    (TP + 'woodpile', None, 21.6, 24.0, 1.6, (0.9, 0.5)),
    (TP + 'cart', None, 9.2, 23.6, 2.2, (0.85, 0.6)),
    (TP + 'lamp_wood', None, 31.0, 30.0, 1.1, (0.4, 0.3)),
    (TP + 'lamp_wood', None, 33.0, 24.0, 1.1, (0.4, 0.3)),
    (FP + '16_cave', '유적 입구 (준비 중)', 2.85, 16.6, 2.6, (0.9, 1.0)),
    (FP + '16_cave', '유적 입구 (준비 중)', 61.15, 16.6, 2.6, (0.9, 1.0)),
]
# 어두운 바깥(못 가는 곳)의 나무 — 마을 가장자리 숲
TREES = [(x, y) for x, y in [
    (6, 8), (12, 7), (18, 9), (46, 8), (52, 7), (58, 9), (3, 33), (8, 36), (5, 42), (10, 47), (17, 48), (24, 47),
    (40, 47), (47, 48), (54, 47), (59, 42), (56, 36), (61, 33), (27, 31.5), (37, 31.5), (2, 12), (62, 12), (44, 3.5), (20, 3.5),
]]

SPAWN = (32.0, 45.5)      # 시작·성 밖에서 돌아올 때(정문 안쪽)
FOUNTAIN_PORTAL = (29.0, 18.0)
# 행인이 돌아다닐 지점(칸)
WP = [(18, 38), (24, 40), (30, 37), (36, 38), (42, 40), (47, 38), (32, 31), (32, 24), (27, 17), (37, 17), (32, 21),
      (8, 27.2), (15, 27.2), (24, 27.2), (40, 27.2), (50, 27.2), (57, 27.2), (8, 20.3), (16, 20.3), (45, 20.3), (55, 20.3)]


def tile_kind():
    """0 = 길, 1 = 건물 터(밝은 풀, 막힘), 2 = 바깥(어둡게, 막힘)"""
    k = np.full((SAND_H, SAND_W), 2, np.int8)
    for y in range(SAND_H):
        for x in range(SAND_W):
            cx, cy = x + 0.5, y + 0.5
            if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in ROADS): k[y, x] = 0
    road = k == 0
    for y in range(SAND_H):
        for x in range(SAND_W):
            if k[y, x] == 0: continue
            if road[y + 1:min(SAND_H, y + 7), x].any(): k[y, x] = 1   # 길 바로 북쪽 6칸 = 건물 터
    return k


def edge_solids(TS):
    k = tile_kind(); out = []
    for y in range(SAND_H):
        x = 0
        while x < SAND_W:
            if k[y, x] == 0: x += 1; continue
            s = x
            while x < SAND_W and k[y, x] != 0: x += 1
            out.append(dict(x0=s * TS, x1=x * TS, y0=y * TS, y1=(y + 1) * TS))
    return out


DARK = (18, 62, 24, 0.49)   # 필드 봄 테마와 같은 어둠
FEATHER = 15                # 게임 픽셀 기준 페더(필드와 동일)


def gen_ground(R, px, seed, cache):
    if os.path.exists(cache): return Image.open(cache).convert('RGB')
    mw, mh = SAND_W, SAND_H
    rng = np.random.RandomState(seed); random.seed(seed)
    W, H = mw * px, mh * px
    def tex(n):
        t = np.asarray(Image.open(R + f'tiles/spring/{n}.png').convert('RGB').resize((px, px), Image.LANCZOS))
        return np.tile(t, (mh, mw, 1)).astype(np.float32)
    grass, flower, cobble, dirt = (tex(n) for n in ('grass', 'grass_flower', 'path', 'dirt'))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) / px
    def noise(scale, amp):
        n = rng.rand(H // 8 + 2, W // 8 + 2).astype(np.float32); n = nd.gaussian_filter(n, scale / 8)
        n = (n - n.mean()) / (n.std() + 1e-6)
        return np.asarray(Image.fromarray(n).resize((W, H), Image.BILINEAR)) * amp
    N1, N2 = noise(24, 0.18), noise(60, 0.5)
    def mask(rects, soft):
        s = np.full((H, W), 1e9, np.float32)
        for x0, y0, x1, y1 in rects:
            dx = np.maximum(x0 - xx, xx - x1); dy = np.maximum(y0 - yy, yy - y1)
            s = np.minimum(s, np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0))
        return np.clip(0.5 - (s + N1 * 0.6) / soft, 0, 1)[..., None]
    img = grass.copy()
    fm = np.zeros((H, W), np.float32)
    for _ in range(18):
        cx, cy, r = random.uniform(1, mw - 1), random.uniform(1, mh - 1), random.uniform(1.0, 2.2)
        fm = np.maximum(fm, np.clip(1.4 - np.hypot(xx - cx, yy - cy) / r + N2 * 0.6, 0, 1))
    img = img * (1 - fm[..., None]) + flower * fm[..., None]
    streets = [r for r in ROADS if r not in PLAZAS]
    md = mask(streets, 0.22)
    img = img * (1 - 0.22 * np.clip(mask(streets, 0.5) - md, 0, 1)); img = img * (1 - md) + dirt * md
    mc = mask(PLAZAS, 0.08)
    img = img * (1 - 0.3 * np.clip(mask(PLAZAS, 0.25) - mc, 0, 1)); img = img * (1 - mc) + cobble * mc
    # 못 가는 곳: 칸 단위 어둠 → 페더(필드 field_dungeon.js와 같은 방식)
    shade = (tile_kind() == 2).astype(np.float32)
    shade = nd.gaussian_filter(np.kron(shade, np.ones((px, px), np.float32)), FEATHER * px / 48)
    a = DARK[3] * shade[..., None]
    img = img * (1 - a) + np.array(DARK[:3], np.float32) * a
    g = Image.fromarray(img.clip(0, 255).astype(np.uint8)); g.save(cache); return g
