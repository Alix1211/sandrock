import base64, io, json, random
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as nd

import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(ROOT, 'assets') + '/'
with open(os.path.join(ROOT,'src','story','quests.json'),encoding='utf-8') as qf:
    MAIN_QUEST_DATA=json.load(qf)
TS = 48          # 게임 단위 칸 크기
PX = 64          # 바닥 그림의 칸당 픽셀
MW, MH = 72, 50  # 판타지 워크숍 큰 마을(칸)
random.seed(7); np.random.seed(7)

CDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.enc_cache')
os.makedirs(CDIR, exist_ok=True)
def enc(img, q=82, fmt='WEBP'):
    # 같은 그림·같은 품질이면 예전에 압축한 결과를 그대로 씀 (빌드 시간 단축)
    import hashlib
    h = hashlib.md5(img.tobytes() + repr((img.size, img.mode, q, fmt)).encode()).hexdigest()
    cp = os.path.join(CDIR, h + '.txt')
    if os.path.exists(cp): return open(cp).read()
    b = io.BytesIO(); img.save(b, fmt, quality=q, method=6)
    out = 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()
    open(cp, 'w').write(out); return out

def tex(path):
    t = Image.open(path).convert('RGB').resize((PX, PX), Image.LANCZOS)
    a = np.asarray(t)
    return np.tile(a, (MH, MW, 1)).astype(np.float32)

W, H = MW * PX, MH * PX
grass = tex(R + 'tiles/spring/grass.png')
flower = tex(R + 'tiles/spring/grass_flower.png')
cobble = tex(R + 'tiles/spring/path.png')
dirt = tex(R + 'tiles/spring/dirt.png')
sand = tex(R + 'tiles/spring/sand.png')
water = tex(R + 'tiles/spring/water.png')

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) / PX   # 칸 좌표
def noise(scale, amp):
    n = np.random.rand(H // 8 + 2, W // 8 + 2).astype(np.float32)
    n = nd.gaussian_filter(n, scale / 8)
    n = (n - n.mean()) / (n.std() + 1e-6)
    n = np.asarray(Image.fromarray(n).resize((W, H), Image.BILINEAR))
    return n * amp
N1 = noise(24, 0.18); N2 = noise(60, 0.5)

def rect_sdf(x0, y0, x1, y1):
    dx = np.maximum(x0 - xx, xx - x1); dy = np.maximum(y0 - yy, yy - y1)
    out = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0))
    inn = np.minimum(np.maximum(dx, dy), 0)
    return out + inn  # 음수 = 안쪽

def mask_from(sdf, soft=0.12, n=None):
    d = sdf + (N1 if n is None else n)
    return np.clip(0.5 - d / soft, 0, 1)[..., None]

CACHE=os.path.join(HERE, '.ground_sandrock_town_v1.png')
import os
def make_ground():
    img = grass.copy()
    # 꽃 풀밭 무더기
    fm = np.zeros((H, W), np.float32)
    for _ in range(16):
        cx, cy, r = random.uniform(1, MW - 1), random.uniform(1, MH - 1), random.uniform(1.0, 2.2)
        fm = np.maximum(fm, np.clip(1.4 - np.hypot(xx - cx, yy - cy) / r + N2 * 0.6, 0, 1))
    img = img * (1 - fm[..., None]) + flower * fm[..., None]

    # ---- 판타지 워크숍 큰 마을: 중앙광장 + 상업/행정/외곽 작업지구 ----
    PLAZA = (25.0, 17.0, 47.0, 27.8)
    COBBLE = [
        PLAZA,
        (34.0, 8.5, 38.5, 30.0),      # 시청-광장 세로축
        (10.0, 19.0, 63.5, 23.7),     # 상업 메인거리
        (14.0, 27.0, 58.5, 30.6),     # 남쪽 상업거리
        (36.8, 27.0, 41.2, 50.5),     # 연못 우측-정문 큰길
        (48.0, 34.0, 64.0, 37.0),     # 주거/작업장 연결
    ]
    DIRT = [
        (8.0, 11.5, 63.5, 15.5),      # 북부 행정/연구 지구
        (7.0, 22.5, 12.0, 42.5),      # 서쪽 자원/창고 지구
        (58.0, 20.5, 66.0, 45.5),     # 동쪽 생산 지구
        (10.0, 33.0, 28.0, 36.5),     # 서남 주거/목공
        (47.0, 39.0, 65.0, 45.5),     # 플레이어/주거 지구
        (20.5, 41.0, 38.5, 45.0),     # 경비대-정문 연결
    ]

    def union(rects):
        s = np.full((H, W), 1e9, np.float32)
        for r in rects: s = np.minimum(s, rect_sdf(*r))
        return s
    sd = union(DIRT)
    md = mask_from(sd, 0.25)
    shade = np.clip(0.5 - (sd + N1 - 0.12) / 0.25, 0, 1)[..., None] - md
    img = img * (1 - 0.25 * np.clip(shade, 0, 1))
    img = img * (1 - md) + dirt * md
    sc = union(COBBLE)
    mc = mask_from(sc, 0.06, N1 * 0.25)
    rim = np.clip(0.5 - (sc - 0.10) / 0.10, 0, 1)[..., None] - mc
    img = img * (1 - 0.35 * np.clip(rim, 0, 1))
    img = img * (1 - mc) + cobble * mc

    # 남쪽 중앙 연못: 샌드록식 '도시의 기억점'. 큰길은 우측으로 우회한다.
    pc = (35.0, 34.4)
    pd = np.hypot((xx - pc[0]) / 5.8, (yy - pc[1]) / 2.6) - 1 + N2 * 0.06
    ms = np.clip(0.5 - (pd - 0.26) / 0.10, 0, 1)[..., None]
    mw = np.clip(0.5 - pd / 0.06, 0, 1)[..., None]
    img = img * (1 - ms) + sand * ms
    img = img * (1 - mw) + water * mw

    # 가장자리 살짝 어둡게
    v = np.clip(np.minimum(np.minimum(xx, MW - xx), np.minimum(yy, MH - yy)) / 2.5, 0, 1)[..., None]
    img = img * (0.72 + 0.28 * v)

    return Image.fromarray(img.clip(0, 255).astype(np.uint8))
if os.path.exists(CACHE):
    ground = Image.open(CACHE).convert('RGB')
else:
    ground = make_ground(); ground.save(CACHE)



# ---- 그림자 (해는 왼쪽 위: 그림자는 오른쪽 아래로 눕는다) ----
def bake_shadows(base, items):
    k = PX / TS
    sh = Image.new('L', base.size, 0)
    for it in items:
        im = Image.open(it['path']).convert('RGBA')
        w = max(1, round(it['w'] * k)); h = max(1, round(it['h'] * k))
        a = im.resize((w, h), Image.LANCZOS).split()[3].point(lambda v: 255 if v > 90 else 0)
        sq = it.get('sq', 0.42); hh = max(1, round(h * sq))
        a = a.resize((w, hh), Image.BILINEAR)
        shear = 0.55
        ow = w + round(hh * shear)
        a = a.transform((ow, hh), Image.AFFINE, (1, shear, -hh * shear, 0, 1, 0), Image.BILINEAR)
        x0 = round(it['x'] * k - w / 2); y0 = round(it['y'] * k - hh)
        foot = round(it.get('foot', 0.05) * h)   # 그림 아래 여백만큼 위로
        sh.paste(255, (x0, y0 - foot), a)
        # 밑동 접지 그림자
        e = Image.new('L', (w, max(4, round(h * 0.12))), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(e).ellipse((w * 0.04, 0, w * 0.96, e.height - 1), fill=200)
        sh.paste(e, (x0, round(it['y'] * k - foot - e.height * 0.6)), e)
    sh = sh.filter(ImageFilter.GaussianBlur(PX * 0.09))
    arr = np.asarray(base).astype(np.float32)
    m = np.asarray(sh).astype(np.float32)[..., None] / 255 * 0.42
    tint = np.array([20, 30, 60], np.float32)
    arr = arr * (1 - m) + tint * m
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))

# ---- 판타지 워크숍 큰 마을 건물 ----
# key, art, 이름, 중심x, 바닥y, 폭(칸), 문 x 보정(폭 비율)
B = [
 ('general_store',   'shop_general',   '잡화점',       27.0, 21.0, 4.5, -0.06),
 ('workshop',        'shop_tools',     '공방',         61.0, 44.2, 5.4,  0.00),
 ('carpentry',       'cottage_thatch', '목공소',       18.0, 35.0, 5.0,  0.00),
 ('research_center', 'scholar_dome',   '연구센터',     24.0, 13.4, 5.2,  0.00),
 ('city_hall',       'castle',         '시청',         36.0, 12.8, 6.8,  0.00),
 ('recycling',       'smithy',         '재활용소',      9.5, 24.7, 5.0, -0.04),
 ('material_shop',   'shop_general',   '재료상',       45.0, 21.0, 4.5,  0.05),
 ('blacksmith',      'smithy',         '대장간',       58.0, 22.0, 5.2, -0.05),
 ('clothing',        'townhouse_pawn', '의류점',       51.5, 21.0, 4.4,  0.00),
 ('mine_office',     'manor_vault',    '광산 관리소',  13.0, 13.8, 5.0,  0.00),
 ('guild_hall',      'guild_hall',     '길드',         36.0, 18.0, 5.8,  0.00),
 ('post_office',     'house_blue',     '우체국',       20.5, 21.0, 4.4,  0.00),
 ('inn',             'tavern',         '여관',         36.0, 30.0, 5.3,  0.02),
 ('restaurant',      'tavern',         '식당',         28.0, 30.0, 5.0,  0.02),
 ('pharmacy',        'shop_general',   '약방',         44.0, 30.0, 4.4, -0.04),
 ('warehouse',       'manor_vault',    '창고',          9.5, 35.0, 5.2,  0.00),
 ('trading_post',    'shop_tools',     '교역소',       51.0, 30.0, 4.8,  0.00),
 ('residence',       'house_red',      '민가',         53.0, 40.5, 4.8,  0.00),
 ('ruin_office',     'scholar_dome',   '유적 관리소',  58.0, 13.8, 5.1,  0.00),
 ('community_hall',  'guild_hall',     '마을회관',     47.5, 13.4, 5.2,  0.00),
 ('mansion',         'manor_vault',    '저택',         61.0, 35.2, 5.6,  0.00),
 ('abandoned',       'cottage_thatch', '폐건물',       10.5, 42.3, 4.8,  0.00),
 ('guard_hq',        'guild_hall',     '경비대',       26.0, 43.5, 6.0,  0.00),
 ('gate_twin_tower', 'gate_twin_tower','정문 (성 밖으로)',36.0, 50.0, 7.0, 0.00),
]
SCALE = 1.5
imgs = {}
for _, art, _, _, _, _, _ in B:
    if art in imgs: continue
    imgs[art] = Image.open(R + f'buildings/{art}.png').convert('RGBA')
blds = []
assets = {}
for k, art, name, cx, by, wt, dxr in B:
    im = imgs[art]
    w = wt * TS; h = w * im.height / im.width
    if k not in assets:
        assets[k] = enc(im.resize((round(w * SCALE), round(h * SCALE)), Image.LANCZOS))
    blds.append(dict(k=k, art=art, name=name, x=cx * TS, y=by * TS, w=w, h=h, door=dxr))

# 소품 (건물 부품 중 바닥에 세울 수 있는 것만)
# 소품: key, 이름(살펴보기), x, 바닥y, 폭(칸), 충돌(폭 비율, 깊이 칸) — 충돌 0이면 통과
TP = 'town_props/'; BP = 'building_parts/'
P = [
 (TP+'personal_stash_closed','개인 창고',59.0,45.1,1.3,(0.8,0.45)),
 (TP+'fountain',None,36.0,25.2,4.2,(0.86,1.3)),
 (BP+'part_36','의뢰 게시판',40.2,18.9,1.5,(0.8,0.3)),
 (TP+'signpost','이정표',39.8,28.2,1.2,(0.4,0.3)),
 (TP+'well','우물',49.0,39.0,2.4,(0.8,0.9)),
 (TP+'stall_blue','노점',23.5,25.5,3.0,(0.85,0.9)),
 (TP+'stall_red','노점',48.5,25.5,3.0,(0.85,0.9)),
 (TP+'bench_iron',None,31.0,26.3,2.0,(0.9,0.5)),
 (TP+'bench_iron',None,41.0,26.3,2.0,(0.9,0.5)),
 (TP+'bench_stone',None,36.0,28.2,2.1,(0.9,0.5)),
 (TP+'woodpile',None,20.0,35.8,1.9,(0.9,0.5)),
 (TP+'hay',None,21.8,35.8,1.8,(0.85,0.6)),
 (TP+'cart',None,12.0,36.2,2.4,(0.85,0.6)),
 (TP+'barrel_bucket',None,56.0,22.7,1.4,(0.8,0.4)),
 (TP+'barrel_bucket',None,49.5,30.8,1.4,(0.8,0.4)),
 (TP+'lamp_iron',None,27.0,24.2,1.0,(0.5,0.3)),
 (TP+'lamp_iron',None,45.0,24.2,1.0,(0.5,0.3)),
 (TP+'lamp_iron',None,31.0,18.0,1.0,(0.5,0.3)),
 (TP+'lamp_iron',None,41.0,18.0,1.0,(0.5,0.3)),
 (TP+'lamp_wood',None,38.8,31.0,1.1,(0.4,0.3)),
 (TP+'lamp_wood',None,40.0,39.0,1.1,(0.4,0.3)),
 (TP+'tree_big',None,18.0,17.2,4.0,(0.16,0.3)),
 (TP+'tree_blossom',None,23.0,17.0,3.2,(0.16,0.3)),
 (TP+'tree_big',None,50.0,17.0,4.0,(0.16,0.3)),
 (TP+'tree_small',None,55.0,17.5,3.0,(0.16,0.3)),
 (TP+'tree_big',None,28.5,37.8,4.0,(0.16,0.3)),
 (TP+'tree_small',None,43.5,38.0,3.0,(0.16,0.3)),
 (TP+'tree_blossom',None,47.0,45.0,3.2,(0.16,0.3)),
 (TP+'tree_big',None,67.0,31.0,4.0,(0.16,0.3)),
 (TP+'tree_small',None,5.0,30.0,3.0,(0.16,0.3)),
]
props = []
for k, name, cx, by, wt, col in P:
    im = Image.open(R + k + '.png').convert('RGBA')
    w = wt * TS; h = w * im.height / im.width
    key = k.split('/')[-1]
    if key not in assets: assets[key] = enc(im.resize((round(w * SCALE), round(h * SCALE)), Image.LANCZOS))
    props.append(dict(kind='stash' if key=='personal_stash_closed' else None,k=key, path=k, name=name, x=cx * TS, y=by * TS, w=w, h=h, cw=col[0], cd=col[1] * TS, tree=key.startswith('tree')))


_stash_open=Image.open(R+TP+'personal_stash_open.png').convert('RGBA')
_stash_width=1.3*TS*SCALE
assets['personal_stash_open']=enc(_stash_open.resize((round(_stash_width),round(_stash_width*_stash_open.height/_stash_open.width)),Image.LANCZOS))

# 행인 걷기 (옆모습은 왼쪽을 봄)
VIL = [('youth', 1.0, 'residence'), ('kid', 0.82, 'inn'), ('grandpa', 0.95, 'community_hall'), ('maiden', 0.97, 'restaurant'), ('auntie', 0.97, 'general_store')]
vils = []
for name, sc, home in VIL:
    fr = {}
    for d in ['front', 'back', 'side']:
        L = []
        for i in range(5):
            im = Image.open(R + f'characters/villager_{name}/{d}_{i}.png').convert('RGBA')
            h = 98 * sc; w = h * im.width / im.height
            L.append(enc(im.resize((round(w * SCALE), round(h * SCALE)), Image.LANCZOS), 86))
        fr[d] = L
    vils.append(dict(name=name, sc=sc, home=home, w=w, h=h, fr=fr))

# 플레이어: sandrock에서는 루시에라 5x3 걷기 시트를 우선 사용한다.
# 850x516 = 170x172 프레임 5칸 x [정면/후면/측면] 3줄.
el = {}
_player_sheet_path = R + 'characters/luciera_walk.png'
_ps = None
if os.path.exists(_player_sheet_path):
    try:
        _ps = Image.open(_player_sheet_path).convert('RGBA')
    except Exception:
        _ps = None
if _ps is not None:
    if _ps.size != (850, 516):
        _ps = _ps.resize((850, 516), Image.LANCZOS)
    for row, d in enumerate(['front', 'back', 'side']):
        el[d] = [enc(_ps.crop((i*170, row*172, (i+1)*170, (row+1)*172)), 88) for i in range(5)]
    _f0 = _ps.crop((0, 0, 170, 172))
    face = _f0.crop((30, 5, 140, 115)).resize((128, 128), Image.LANCZOS)
else:
    # 원본 ARPG 에셋 폴백
    for d in ['front', 'back', 'side']:
        fr = []
        for i in range(5):
            im = Image.open(R + f'characters/elf/{d}_{i}.png').convert('RGBA')
            fr.append(enc(im.resize((170, 172), Image.LANCZOS), 88))
        el[d] = fr
    face = Image.open(R + 'characters/elf/front_0.png').convert('RGBA').crop((105, 45, 275, 215)).resize((128, 128), Image.LANCZOS)

# ---- 본편 반복 등장 캐릭터 초상(기존 사용자 제공 에셋 재사용) ----
STORY_CHARS={}
for sid,nm,title,folder in [
    ('hero','카엘렌','떠돌이 검사','hero'),
    ('knight','러스티','이계의 용병','knight'),
]:
    im=Image.open(R+f'characters/{folder}/front_0.png').convert('RGBA')
    pt=im.copy(); pt.thumbnail((520,560),Image.LANCZOS)
    STORY_CHARS[sid]=dict(name=nm,title=title,port=enc(pt,88))

_shadow=Image.open(R+'npc_hd/npc_35.png' if os.path.exists(R+'npc_hd/npc_35.png') else R+'npc/npc_35.png').convert('RGBA')
_shadow.thumbnail((520,560),Image.LANCZOS)
STORY_CHARS['shadow']=dict(name='???',title='',port=enc(_shadow,88))

# ---- 테스트 동행 캐릭터 걷기 프레임(검사/총병) ----
COMPANIONS={}
for sid,nm,title,folder in [
    ('hero','카엘렌','검사 · 파티 테스트','hero'),
    ('knight','러스티','이계의 용병 · 총병','knight'),
]:
    fr={}
    for d in ['front','back','side']:
        arr=[]
        for i in range(5):
            im=Image.open(R+f'characters/{folder}/{d}_{i}.png').convert('RGBA')
            hh=172; ww=max(1,round(hh*im.width/im.height))
            arr.append(enc(im.resize((ww,hh),Image.LANCZOS),88))
        fr[d]=arr
    COMPANIONS[sid]=dict(name=nm,title=title,fr=fr)

ui = {}
for k in ['03', '04', '05', '06', '14', '15']:
    ui[k] = enc(Image.open(R + f'ui/kit_c/kit_c_{k}.png').convert('RGBA'), 90)

# ---- 사람 (시나리오 장부 번호 = 초상화 번호) ----
# 번호, 이름, 직함, 건물 key(문 옆에 섬) 또는 None, x, y(칸, 건물 없을 때), 왼쪽(-1)/오른쪽(1), 첫마디, 가게 종류
NPC = [
 (1,  '마르코','잡화점 주인',      'general_store',   1,'오늘은 물건보다 사람이 먼저 들어오네요. 천천히 둘러보세요.','general'),
 (2,  '레오',  '공방 관리인',      'workshop',       -1,'아침부터 톱밥이 날리더니 이제야 좀 조용해졌네요.',None),
 (3,  '하겐',  '목공소 주인',      'carpentry',       1,'나무는 결을 거슬러 자르면 꼭 티를 냅니다. 사람도 비슷하고요.',None),
 (4,  '에드먼','연구원',           'research_center',-1,'잠깐만요. 방금 떠오른 걸 적고 있었는데… 네, 이제 말씀하시죠.',None),
 (5,  '오토',  '시청 담당관',      'city_hall',       1,'광장 쪽 공사가 끝나니 민원이 절반은 줄었군요. 나머지 절반은 사람 문제고요.',None),
 (6,  '리코',  '재활용소 주인',    'recycling',      -1,'버리는 것과 쓸모없는 건 다른 말입니다. 여기선 특히 그래요.',None),
 (7,  '미라',  '재료상',           'material_shop',   1,'재료는 눈으로만 보면 다 비슷해요. 손에 올려보면 바로 다르죠.','general'),
 (8,  '그레타','대장장이',         'blacksmith',     -1,'불 가까이 오지 마요. 말은 들리니까 거기서 해도 됩니다.','arms'),
 (9,  '루나',  '의류점 주인',      'clothing',        1,'옷은 멀쩡해 보여도 실밥 하나가 하루 종일 신경 쓰일 때가 있죠.',None),
 (10, '도란',  '광산 관리인',      'mine_office',    -1,'오늘 갱도 보고서는 아직 덜 왔습니다. 늘 그렇죠.',None),
 (11, '하르트','길드장',           'guild_hall',      1,'게시판은 새로 정리했습니다. 누가 순서를 또 바꾸지만 않으면요.','guild'),
 (12, '리아',  '우체국 직원',      'post_office',    -1,'편지는 쌓이는데 사람은 늘 급하네요. 그래도 잃어버리진 않습니다.',None),
 (13, '토비',  '여관 주인',        'inn',             1,'방은 비어 있어요. 불도 지펴놨고요. 들어가실 거면 말씀하세요.','inn'),
 (14, '브란',  '식당 주인',        'restaurant',     -1,'냄비는 끓고 있고 자리는 남았습니다. 둘 중 하나는 금방 없어지겠죠.',None),
 (15, '세라',  '약사',             'pharmacy',        1,'약초 냄새가 좀 세죠? 익숙해지면 오히려 밖이 밋밋합니다.','general'),
 (16, '모건',  '창고지기',         'warehouse',      -1,'들어온 상자보다 나간 상자가 적군요. 오늘도 정리할 게 많겠습니다.',None),
 (17, '핀',    '교역소 직원',      'trading_post',    1,'시세판은 아침에 갈았습니다. 오후엔 또 달라질지도 모르지만요.','trade'),
 (18, '미나',  '주민',             'residence',      -1,'집 앞이 전보다 조용해졌어요. 광장 쪽으로 사람들이 몰려서 그런가 봐요.',None),
 (19, '베른',  '유적 관리인',      'ruin_office',     1,'유적에서 가져온 건 먼저 기록부터 합니다. 손대는 건 그다음이고요.',None),
 (20, '엘다',  '마을회관 관리인',  'community_hall', -1,'회의가 끝나면 의자가 꼭 하나씩 엉뚱한 데 가 있습니다.',None),
 (21, '페닉스','저택 관리인',      'mansion',         1,'주인께선 안에 계십니다. 만나실 수 있다는 뜻은 아니지만요.',None),
 (22, '고르던','폐건물 관리인',    'abandoned',      -1,'폐건물이라고 아무나 들어가도 되는 건 아닙니다. 바닥이 먼저 항의할 겁니다.',None),
 (23, '라이너','경비병',           'guard_hq',        1,'순찰 교대까지 조금 남았습니다. 정문 쪽은 이상 없습니다.',None),
 (24, '에다',  '경비병',           'guard_hq',       -1,'라이너는 기록부터 보고, 나는 사람 얼굴부터 봐요. 둘 다 필요하죠.',None),
]
bpos = {b['k']: b for b in blds}
PORT = {}
npcs = []
for no, name, title, where, side, line, shop in NPC:
    hd = R + f'npc_hd/npc_{no:02d}.png'
    im = Image.open(hd if os.path.exists(hd) else R + f'npc/npc_{no:02d}.png').convert('RGBA')
    pt = im.copy(); pt.thumbnail((520, 560), Image.LANCZOS); PORT[f'npc_{no:02d}'] = enc(pt, 88)
    h = 100; w = h * im.width / im.height
    key = f'npc_{no:02d}'
    assets[key] = enc(im.resize((round(w * SCALE), round(h * SCALE)), Image.LANCZOS), 88)
    if isinstance(where, tuple):
        x, y = where[1] * TS, where[2] * TS
    else:
        b = bpos[where]; x = b['x'] + b['door'] * b['w'] + side * (b['w'] * 0.28); y = b['y'] + 0.55 * TS
    npcs.append(dict(k=key, no=no, name=name, title=title, x=x, y=y, w=w, h=h, line=line, shop=shop, at=where if isinstance(where, str) else None))

# 마을광장 임시 테스트 인원. 검증이 끝나면 배치만 숨기고 시스템은 유지한다.
for _sid,_x,_line in [
    ('hero',19.2,'검 손질은 끝났습니다. 같이 나가 보시죠. 비용은… 선불로 받겠습니다.'),
    ('knight',26.8,'탄약은 제가 챙깁니다. 대신 하루치 계산은 출발 전에 끝내죠.'),
]:
    _src=R+f"characters/{_sid}/front_0.png"
    _im=Image.open(_src).convert('RGBA'); _h=100; _w=_h*_im.width/_im.height
    _key='companion_'+_sid
    assets[_key]=enc(_im.resize((round(_w*SCALE),round(_h*SCALE)),Image.LANCZOS),88)
    PORT[_key]=STORY_CHARS[_sid]['port']
    npcs.append(dict(k=_key,no=0,name=COMPANIONS[_sid]['name'],title=COMPANIONS[_sid]['title'],
                     x=_x*TS,y=22.35*TS,w=_w,h=_h,line=_line,shop=None,at=None,companion=_sid,companionTest=True))

# 퀘스트 장면에만 등장하는 NPC 초상도 미리 담는다. 마을 NPC로 배치하지는 않는다.
_story_portrait_nos=set()
for _q in MAIN_QUEST_DATA.get('quests',[])+MAIN_QUEST_DATA.get('sideQuests',[]):
    for _s in _q.get('steps',[]):
        if _s.get('portraitNpc') is not None:
            _story_portrait_nos.add(int(_s['portraitNpc']))
for _no in sorted(_story_portrait_nos):
    _key=f'npc_{_no:02d}'
    if _key in PORT: continue
    _hd=R+f'npc_hd/npc_{_no:02d}.png'
    _sd=R+f'npc/npc_{_no:02d}.png'
    _src=_hd if os.path.exists(_hd) else _sd
    if not os.path.exists(_src):
        raise FileNotFoundError(f'퀘스트 초상 누락: {_key}')
    _im=Image.open(_src).convert('RGBA'); _pt=_im.copy(); _pt.thumbnail((520,560),Image.LANCZOS)
    PORT[_key]=enc(_pt,88)


# ---- 큰 마을 여관 실내(1단계) ----
INN_W, INN_H = 14, 10
_inn_floor = Image.open(R + 'interior/int_03.png').convert('RGB').resize((TS, TS), Image.LANCZOS)
_inn_wall = Image.open(R + 'interior/int_12.png').convert('RGB').resize((TS, TS), Image.LANCZOS)
inn_ground = Image.new('RGB', (INN_W * TS, INN_H * TS), (70, 47, 30))
for yy in range(INN_H):
    for xx in range(INN_W): inn_ground.paste(_inn_floor, (xx * TS, yy * TS))
for xx in range(INN_W): inn_ground.paste(_inn_wall, (xx * TS, 0))
# 둘레 벽(돌벽) + 아래쪽 가운데 출입문. 문 틈은 x 6.2~7.8칸.
_inn_stone = Image.open(R + 'interior/int_19.png').convert('RGB').resize((TS, TS), Image.LANCZOS)
_inn_door = Image.open(R + 'interior/int_20.png').convert('RGB').resize((round(1.6 * TS), TS), Image.LANCZOS)
for yy in range(1, INN_H):
    inn_ground.paste(_inn_stone, (0, yy * TS)); inn_ground.paste(_inn_stone, ((INN_W - 1) * TS, yy * TS))
for xx in range(INN_W): inn_ground.paste(_inn_stone, (xx * TS, (INN_H - 1) * TS))
inn_ground.paste(_inn_floor, (round(6.2 * TS), (INN_H - 1) * TS))   # 문 틈 바닥
for xx in (6, 7): inn_ground.paste(_inn_floor, (xx * TS, (INN_H - 1) * TS))
inn_ground.paste(_inn_door, (round(6.2 * TS), (INN_H - 1) * TS))
INN_SOLIDS = [dict(x0=0, x1=INN_W * TS, y0=0, y1=.9 * TS),
              dict(x0=0, x1=TS * .95, y0=0, y1=INN_H * TS), dict(x0=(INN_W - .95) * TS, x1=INN_W * TS, y0=0, y1=INN_H * TS),
              dict(x0=0, x1=6.2 * TS, y0=(INN_H - .9) * TS, y1=INN_H * TS), dict(x0=7.8 * TS, x1=INN_W * TS, y0=(INN_H - .9) * TS, y1=INN_H * TS)]

def _inn_prop(key, src, cx, by, wt, cw=.8, cd=.45, kind=None):
    im = Image.open(R + f'interior/{src}.png').convert('RGBA')
    box = im.getbbox()
    if box: im = im.crop(box)
    w = wt * TS; h = w * im.height / im.width
    k = 'inn_' + key
    assets[k] = enc(im.resize((round(w * SCALE), round(h * SCALE)), Image.LANCZOS), 88)
    return dict(k=k, name=None, x=cx*TS, y=by*TS, w=w, h=h, cw=cw, cd=cd*TS, tree=False, kind=kind)

inn_props = [
    _inn_prop('fireplace','int_49',2.0,2.75,2.05,.78,.7,'fire'),
    _inn_prop('counter','int_25',9.5,3.55,3.4,.92,.62),
    _inn_prop('round_table','int_23',4.2,5.7,2.25,.78,.58),
    _inn_prop('long_table','int_24',9.2,6.05,3.45,.86,.62),
    _inn_prop('bookshelf','int_44_bookshelf',12.1,2.75,1.6,.82,.52),
    _inn_prop('bench','int_31',4.1,8.0,2.2,.88,.35),
    _inn_prop('cabinet','int_36',12.0,6.75,1.35,.78,.48),
]
_toby = next(n for n in npcs if n['no'] == 13)
inn_npcs = [dict(k='npc_13', no=13, name='토비', title='여관 주인', x=9.5*TS, y=4.35*TS,
                 w=_toby['w'], h=_toby['h'], line='왔네요. 불가 쪽 자리는 따뜻해요. 아까 누가 젖은 장갑을 올려놔서 냄새는 조금 나지만요.', shop='inn', at=None)]
INN_BACK = [bpos['inn']['x'], bpos['inn']['y'] + 0.72*TS]
INN = dict(
    map=dict(w=INN_W,h=INN_H,ts=TS,px=PX), ground=enc(inn_ground,86),
    mini=enc(inn_ground.resize((INN_W*6,INN_H*6),Image.LANCZOS),86),
    blds=[], props=inn_props, npcs=inn_npcs, name='여관', spawn=[7.0*TS,8.45*TS], back=INN_BACK,
    solids=INN_SOLIDS,
    exits=[dict(x0=6.15*TS,x1=7.85*TS,y0=9.05*TS,y1=9.85*TS,to='town',pos=INN_BACK,dir='front')]
)

# 승인표의 모든 장비를 명시적으로 로딩(없는 이미지 대체 금지)
with open(os.path.join(HERE, 'data/tier_match.json'), encoding='utf-8') as f:
    CATALOG = json.load(f)
ICON = {}
def icon(path):
    im = Image.open(path).convert('RGBA'); im.thumbnail((96,96), Image.LANCZOS); return enc(im,88)
for item in CATALOG['gear']:
    ICON[item['icon']] = icon(os.path.join(ROOT,item['file']))
# 이전 상점/검사 아이콘 별칭. 신규 생성은 baseId를 사용한다.
for i,kind in enumerate(['head','body','hands','feet']): ICON[f'armor_{i}']=ICON[f'knight_{kind}_02']
for kind,row in [('ring',0),('neck',1)]:
    for i in range(1,6): ICON[f'{kind}_{i}']=ICON[f'acc_{row}_{i:02d}']
    ICON[kind]=ICON[f'acc_{row}_01']


SH = [dict(path=R + f"buildings/{b['art']}.png", x=b['x'], y=b['y'], w=b['w'], h=b['h'], sq=0.5 if b['k'] == 'gate_twin_tower' else 0.42) for b in blds]
SH += [dict(path=R + p['path'] + '.png', x=p['x'], y=p['y'], w=p['w'], h=p['h'], sq=0.55 if p['tree'] else 0.5, foot=0.03) for p in props]
ground = bake_shadows(ground, SH)
mini = ground.resize((MW * 6, MH * 6), Image.LANCZOS)

# 인터페이스용 키트 그림
KIT = {}
for k in ['01', '02', '02b', '18', '21', '14']:
    KIT[k] = enc(Image.open(R + f'ui/kit_c/kit_c_{k}.png').convert('RGBA'), 90)
tabs = Image.open(R + 'ui/kit_c/kit_c_11.png').convert('RGBA')
for i, (x, y, w, h) in enumerate([(6, 4, 79, 72), (89, 4, 81, 72), (175, 5, 80, 71), (260, 4, 79, 72), (346, 3, 77, 73)]):
    KIT[f'tab{i}'] = enc(tabs.crop((max(0, x - 5), 0, min(tabs.width, x + w + 5), tabs.height)), 90)
for k, f in [('swap', '29_btn_swap'), ('bag', '28_btn_bag'), ('close', '36_btn_close'), ('php', '31_btn_potion_hp'), ('pmp', '32_btn_potion_mp')]:
    im = Image.open(R + f'ui/hud_icons/{f}.png').convert('RGBA'); im.thumbnail((128, 128), Image.LANCZOS); KIT['h_' + k] = enc(im, 90)
for k, f in [('swap', '29_btn_swap'), ('bag', '28_btn_bag'), ('close', '36_btn_close'), ('php', '31_btn_potion_hp'), ('pmp', '32_btn_potion_mp')]:
    im = Image.open(R + f'ui/hud_icons/{f}.png').convert('RGBA'); im.thumbnail((128, 128), Image.LANCZOS); KIT['h_' + k] = enc(im, 90)
for k, f in [('scr_portal', 'scroll_closed'), ('scr_ident', 'scroll_magic')]:
    im = Image.open(R + f'ui/{f}.png').convert('RGBA'); im.thumbnail((128, 128), Image.LANCZOS); KIT['h_' + k] = enc(im, 90)
WPNI = {}
for t in ['sword', 'spear', 'gauntlet', 'bow', 'staff']:
    for g in range(1, 11):
        im = Image.open(R + f'weapons/{t}_{g:02d}.png').convert('RGBA'); im = im.crop(im.getbbox())
        im.thumbnail((200, 200), Image.LANCZOS); WPNI[f'{t}_{g:02d}'] = enc(im, 88)
s2b = Image.open(R + 'ui/kit_c/kit_c_02b.png').convert('RGBA')
KIT['hpbar'] = enc(Image.open(R + 'ui/hud_clean/bar_hp.png').convert('RGBA'), 92); KIT['mpbar'] = enc(Image.open(R + 'ui/hud_clean/bar_mp.png').convert('RGBA'), 92)   # tools/hud_clean.py로 테두리만 깨끗하게 잘라 낸 막대
KIT['pring'] = enc(Image.open(R + 'ui/hud_clean/portrait_ring.png').convert('RGBA'), 92)   # 안쪽을 뚫은 초상화 고리
rg = Image.open(R + 'ui/hud_icons/ring_empty.png').convert('RGBA'); rg.thumbnail((200, 200), Image.LANCZOS); KIT['ring'] = enc(rg, 90)
SKI = {}
import glob as _g
for f in sorted(_g.glob(R + 'ui/hud_icons/*.png')):
    n = os.path.basename(f)[:-4]
    if not n[:2].isdigit() or int(n[:2]) > 27: continue
    im = Image.open(f).convert('RGBA'); im.thumbnail((112, 112), Image.LANCZOS); SKI[n.split('_', 1)[1]] = enc(im, 88)
if os.path.exists(_player_sheet_path):
    ef = Image.open(_player_sheet_path).convert('RGBA').crop((0, 0, 170, 172))
else:
    ef = Image.open(R + 'characters/elf/front_0.png').convert('RGBA')
ef = ef.crop(ef.getbbox())
ELF_FRONT = enc(ef, 90)

# ---- 필드 7테마 · 몬스터 (런타임 생성용) ----
FIELD_THEMES = ['spring','summer','autumn','winter','ice','volcano','swamp']
FIELD_TILES, FIELD_PROPS = {}, {}
for th in FIELD_THEMES:
    FIELD_TILES[th] = {}
    for nm in ['grass','grass_flower','dirt','path','sand','water']:
        p = R + f'tiles/{th}/{nm}.png'
        if os.path.exists(p):
            im = Image.open(p).convert('RGB').resize((96,96), Image.LANCZOS)
            FIELD_TILES[th][nm] = enc(im, 84)
    FIELD_PROPS[th] = []
    for f in sorted(_g.glob(R + f'field_props/{th}/*.png')):
        stem = os.path.basename(f)[:-4]
        key = 'f_' + th + '_' + stem
        im = Image.open(f).convert('RGBA'); im.thumbnail((360,360), Image.LANCZOS)
        assets[key] = enc(im, 86)
        FIELD_PROPS[th].append(dict(key=key, name=stem))

# 2026-10-05: 전 몬스터 53종 V2 화풍 통일 아틀라스.
# 게임 수치/AI는 tier_match.json을 그대로 쓰고, 방향 그림만 새 아틀라스에서 자른다.
with open(os.path.join(HERE, 'data/monster_visual_v2.json'), encoding='utf-8') as f:
    MONV2 = json.load(f)
if set(MONV2['rows']) != set(CATALOG['monsters']):
    miss=set(CATALOG['monsters'])-set(MONV2['rows']); extra=set(MONV2['rows'])-set(CATALOG['monsters'])
    raise ValueError(f'몬스터 V2 매핑 불일치 missing={sorted(miss)} extra={sorted(extra)}')
V2_CELL = int(MONV2['cell'])
V2_PARTS = {}
for i,fn in enumerate(MONV2['parts'],1):
    V2_PARTS[i] = Image.open(os.path.join(ROOT, 'source_sheets', 'monster_v2', fn)).convert('RGBA')

MON3 = {}
for name,d in CATALOG['monsters'].items():
    images={}
    ref=MONV2['rows'][name]; atlas=V2_PARTS[int(ref['part'])]; row=int(ref['row'])
    for col,direction in enumerate(MONV2['columns']):
        im=atlas.crop((col*V2_CELL,row*V2_CELL,(col+1)*V2_CELL,(row+1)*V2_CELL))
        box=im.getchannel('A').getbbox()
        if not box: raise ValueError('빈 몬스터 V2 셀: '+name+'/'+direction)
        im=im.crop(box); im.thumbnail((240,240),Image.LANCZOS)
        images[direction]=enc(im,86)
    # 미믹의 잠든 상자 모습 같은 보조 이미지는 기존 소품 자산을 유지한다.
    # 전투 중 보이는 몬스터 본체(front/back/left/right)는 모두 V2다.
    for direction,path in d['images'].items():
        if direction in ('front','back','left','right'): continue
        im=Image.open(os.path.join(ROOT,path)).convert('RGBA')
        box=im.getchannel('A').getbbox()
        if not box: raise ValueError('빈 몬스터 보조 이미지: '+path)
        im=im.crop(box); im.thumbnail((240,240),Image.LANCZOS)
        images[direction]=enc(im,86)
    MON3[name]=images
MON1 = {}

# ---- 성 밖 갈림길 들판 ----
import outmap
og = outmap.gen_ground(R, outmap.OUT_W, outmap.OUT_H, PX, outmap.OUT_DIRT, 11, os.path.join(HERE, '.ground_out_cache.png'))
oprops = []
for k, name, cx, by, wt, col, kind in outmap.OUT_PROPS:
    im = Image.open(R + k + '.png').convert('RGBA')
    w = wt * TS; h = w * im.height / im.width
    key = 'o_' + k.replace('/', '_')
    if key not in assets: assets[key] = enc(im.resize((round(w * SCALE), round(h * SCALE)), Image.LANCZOS))
    oprops.append(dict(k=key, path=k, name=name, x=cx * TS, y=by * TS, w=w, h=h, cw=col[0] if col else 0, cd=(col[1] if col else 0) * TS,
                       tree=kind == 'tree', kind=kind))
onpcs = []
_liner = next(n for n in npcs if n['no'] == 1)
for k, name, title, cx, by, hh, line, act in outmap.OUT_NPCS:
    if k == 'guard_cap':
        # 성 안쪽 라이너와 동일 인물. 퀘스트 접근성을 위해 성 밖 갈림길에도 중복 배치한다.
        onpcs.append(dict(k=_liner['k'], no=1, name='라이너', title='성문 경비병', x=cx*TS, y=by*TS,
                          w=_liner['w'], h=_liner['h'], line='성 안에서도 봤겠지만, 밖에선 길부터 확인하십시오.',
                          shop=None, go=None, at=None, questStartAlias='town'))
        continue
    im = Image.open(R + f'npc_guard/{k}.png').convert('RGBA'); w = hh * im.width / im.height
    if k not in assets: assets[k] = enc(im.resize((round(w * SCALE), round(hh * SCALE)), Image.LANCZOS), 88)
    pt = im.copy(); pt.thumbnail((520, 600), Image.LANCZOS); PORT[k] = enc(pt, 88)
    onpcs.append(dict(k=k, name=name, title=title, x=cx * TS, y=by * TS, w=w, h=hh, line=line, shop=None, go=act, at=None))
og = bake_shadows(og, [dict(path=R + p['path'] + '.png', x=p['x'], y=p['y'], w=p['w'], h=p['h'], sq=0.55 if p['tree'] else 0.45, foot=0.03) for p in oprops])
OUT = dict(map=dict(w=outmap.OUT_W, h=outmap.OUT_H, ts=TS, px=PX), ground=enc(og, 80), mini=enc(og.resize((outmap.OUT_W * 6, outmap.OUT_H * 6), Image.LANCZOS), 80),
           blds=[], props=oprops, npcs=onpcs, name='성 밖 갈림길', spawn=[15.0 * TS, 5.7 * TS], back=[23.0 * TS, 27.9 * TS])

# ---- 던전 타일·소품: 두 가지 모습 (ruins=성 밖 입구의 석조 던전, cave=필드 동굴 입구의 자연 동굴) ----
DTI = {}; DPR = {}
RUINS_PROPS = [('stairs_up', 'tiles/stairs_up', 1.0, 0, 0), ('stairs_down', 'tiles/stairs_down', 1.0, 0, 0), ('torch', 'props/torch', 0.55, 0, 0),
               ('pillar', 'props/pillar', 1.1, 0.6, 0.5), ('chest_closed', 'props/chest_closed', 1.0, 0.8, 0.4), ('chest_open', 'props/chest_open', 1.0, 0.8, 0.4),
               ('barrel', 'props/barrel', 0.8, 0.7, 0.35), ('jar', 'props/jar', 0.6, 0.6, 0.3), ('bones', 'props/bones', 0.9, 0, 0), ('cobweb', 'props/cobweb', 1.0, 0, 0)]
CAVE_PROPS = [('stairs_up', 'tiles/stairs_up', 1.0, 0, 0), ('stairs_down', 'tiles/stairs_down', 1.0, 0, 0), ('torch', 'props/torch', 0.55, 0, 0),
              ('pillar', 'props/pillar', 1.0, 0.6, 0.5), ('chest_closed', 'props/chest_closed', 1.0, 0.8, 0.4), ('chest_open', 'props/chest_open', 1.0, 0.8, 0.4),
              ('barrel', 'props/barrel', 0.8, 0.7, 0.35), ('jar', 'props/jar', 0.65, 0.6, 0.3), ('bones', 'props/bones', 1.0, 0, 0), ('cobweb', 'props/cobweb', 1.0, 0, 0),
              ('stalagmites', 'props/stalagmites', 1.2, 0.8, 0.4), ('mushroom', 'props/mushroom', 0.8, 0, 0), ('crystal', 'props/crystal', 0.95, 0.5, 0.3),
              ('rocks', 'props/rocks', 1.1, 0.7, 0.35), ('minecart', 'props/minecart', 1.05, 0.8, 0.4)]
for th, folder, pre, plist in [('ruins', 'dungeon', 'd_', RUINS_PROPS), ('cave', 'dungeon_cave', 'dc_', CAVE_PROPS)]:
    DTI[th] = {}; DPR[th] = {}
    for k in ['floor', 'floor_crack', 'floor_moss', 'wall_front', 'wall_front_moss', 'wall_top']:
        im = Image.open(R + f'{folder}/tiles/{k}.png').convert('RGB').resize((TS, TS), Image.LANCZOS); DTI[th][k] = enc(im, 85)
    for k, src, wt, cw, cd in plist:
        im = Image.open(R + f'{folder}/{src}.png').convert('RGBA'); im = im.crop(im.getbbox())
        w = wt * TS; h = w * im.height / im.width
        assets[pre + k] = enc(im.resize((round(w * SCALE), round(h * SCALE)), Image.LANCZOS), 86)
        DPR[th][k] = dict(src=assets[pre + k], key=pre + k, w=w, h=h, cw=cw, cd=cd)

# 효과음 파일이 있으면 합성음 대신 씀: assets/sfx/<이름>.mp3 (docs/sound_list.md)
SFXF = {}
for f in sorted(_g.glob(R + 'sfx/*.mp3')):
    SFXF[os.path.basename(f)[:-4]] = 'data:audio/mpeg;base64,' + base64.b64encode(open(f, 'rb').read()).decode()
for f in sorted(_g.glob(R + 'sfx/*.ogg')):
    SFXF[os.path.basename(f)[:-4]] = 'data:audio/ogg;base64,' + base64.b64encode(open(f, 'rb').read()).decode()
BGMF = {}
for name in ('town', 'field', 'dungeon', 'boss', 'event'):
    f = R + 'bgm/' + name + '.mp3'
    if os.path.exists(f):
        BGMF[name] = 'data:audio/mpeg;base64,' + base64.b64encode(open(f, 'rb').read()).decode()
# 전투 이펙트 그림(assets/vfx, tools/vfx_slice.py로 시트에서 자른 것). 쓰는 종류만, 종류별 최대 크기로 줄여 담는다.
VFXA = {}
VFX_MAX = {'burst_': 224, 'hit_': 128, 'shot_': 128, 'ring_': 256, 'heal_': 240, 'status_icon_': 56, 'status_down_': 56, 'status_ground_': 128}
for f in sorted(_g.glob(R + 'vfx/*.png')):
    nm = os.path.basename(f)[:-4]
    mx = next((v for k, v in VFX_MAX.items() if nm.startswith(k)), 0)
    if not mx: continue
    im = Image.open(f).convert('RGBA'); im.thumbnail((mx, mx), Image.LANCZOS)
    VFXA[nm] = enc(im, 86)
# 야영지 쉬기 일러스트(낮/밤). 가로 1100으로 줄여 담는다.
CAMPART = {}
for nm in ('day','night'):
    im = Image.open(R + f'illustrations/camp_{nm}.png').convert('RGB'); im.thumbnail((1100,1100), Image.LANCZOS); CAMPART[nm] = enc(im, 84)
# 무역 수레 탈것 일러스트(배경 투명, 원본 시트는 source_sheets/mounts)
MOUNTART = {}
for nm in ('pack','donkey','boar','ox','bear'):
    im = Image.open(R + f'trade/mount_{nm}.png').convert('RGBA'); im.thumbnail((520,520), Image.LANCZOS); MOUNTART[nm] = enc(im, 88)
A = dict(mainQuests=MAIN_QUEST_DATA, storyChars=STORY_CHARS, companions=COMPANIONS, tierCatalog=CATALOG, camp=CAMPART, mounts=MOUNTART, vfx=VFXA, inn=INN, ground=enc(ground, 80), mini=enc(mini, 80), face=enc(face, 90), b=assets, elf=el, ui=ui,
         map=dict(w=MW, h=MH, ts=TS, px=PX), blds=blds, props=props, npcs=npcs, icons=ICON, port=PORT, vils=vils, kit=KIT, elfFront=ELF_FRONT, wpn=WPNI, out=OUT, skicon=SKI, field=dict(tiles=FIELD_TILES, props=FIELD_PROPS), monsters3=MON3, monsters1=MON1, dtiles=DTI, dprops=DPR, sfx=SFXF, bgm=BGMF)
def source(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f: return f.read()
js = source('tier_match.js') + '\n' + source('town.js')
js = js.replace('/*FIELD_DUNGEON*/', source('vfx.js') + '\n' + source('skills2.js') + '\n' + source('inn.js') + '\n' + source('chat.js') + '\n' + source('telemetry.js') + '\n' + source('field_dungeon.js') + '\n' + source('companion.js') + '\n' + source('dungeon.js') + '\n' + source('sound.js') + '\n' + source('bgm.js') + '\n' + source('backup.js') + '\n' + source('trade.js') + '\n' + source('guild.js') + '\n' + source('quest.js'))
html = source('shell.html').replace('/*SAVE_SYNC*/', source('save_sync.js'))
js += '\n' + source('ui.js')
import time as _t
html = html.replace('/*VER*/', _t.strftime('%m%d-%H%M', _t.gmtime(_t.time() + 9 * 3600)))   # 한국시간(서버가 UTC라 +9시간)
# 그림(data:)은 따로 game/art_<해시>.js 로 뺀다 — 그림이 안 바뀌면 파일 이름도 그대로라서
# 앱·브라우저가 한 번 받은 그림을 다시 받지 않고, 평소 업데이트는 가벼운 town.html 만 받는다.
ART = []
def _pull(o):
    if isinstance(o, str) and o.startswith('data:'):
        ART.append(o); return '@@' + str(len(ART) - 1)
    if isinstance(o, dict): return {k: _pull(v) for k, v in o.items()}
    if isinstance(o, list): return [_pull(v) for v in o]
    return o
A2 = _pull(A)
import hashlib, glob
art_js = 'window.ART=' + json.dumps(ART) + ';'
art_name = 'art_' + hashlib.sha1(art_js.encode()).hexdigest()[:10] + '.js'
GAME_DIR = os.path.join(ROOT, 'game')
for old_art in glob.glob(os.path.join(GAME_DIR, 'art_*.js')):
    if os.path.basename(old_art) != art_name: os.remove(old_art)
if not os.path.exists(os.path.join(GAME_DIR, art_name)):
    with open(os.path.join(GAME_DIR, art_name), 'w', encoding='utf-8') as f: f.write(art_js)
RESOLVE = ("const A=(function r(o){if(typeof o==='string')return o.startsWith('@@')?window.ART[+o.slice(2)]:o;"
           "if(Array.isArray(o))return o.map(r);if(o&&typeof o==='object'){for(const k in o)o[k]=r(o[k]);}return o;})(")
# WebView가 이전 그림 묶음을 잘못 캐시한 경우를 끊기 위한 캐시 세대값.
# 그림 해시는 그대로 쓰되 세대값을 올리면 APK가 반드시 새 URL로 다시 받는다.
ART_CACHE_EPOCH = '2'
html = html.replace('<script>\n/*ASSETS*/', '<script src="' + art_name + '?v=' + ART_CACHE_EPOCH + '"></script>\n<script>\n/*ASSETS*/')
html = html.replace('/*ASSETS*/', RESOLVE + json.dumps(A2, ensure_ascii=False) + ');').replace('/*GAME*/', js)
with open(os.path.join(GAME_DIR, 'town.html'), 'w', encoding='utf-8') as f: f.write(html)
print('ok', len(html) // 1024, 'KB +', art_name, len(art_js) // 1024, 'KB')
