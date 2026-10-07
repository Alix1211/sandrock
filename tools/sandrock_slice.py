"""샌드락 시트 자동 자르기.
source_sheets/sandrock/*.png  →  assets/sandrock/<종류>/<이름>.png  (+ manifest.json)

- 시트는 모두 배경 투명(대화창에서 어둡게 보이는 것은 투명 영역에 남은 색일 뿐).
- 테두리 번짐 정리: 아주 옅은 알파(<FRINGE)는 지우고, 반투명 가장자리 픽셀의 색은
  가장 가까운 불투명 픽셀 색으로 바꿔 빨강·노랑 번짐을 없앤다(알파=부드러운 테두리는 유지).
- 그림 덩어리를 자동으로 찾아 위→아래, 왼→오른 순서로 이름표(tools/sandrock_names.py)를 붙인다.
- 개수가 이름표와 다르면 멈추고 알린다(조용히 틀린 이름이 붙는 것 방지).
사용: python3 tools/sandrock_slice.py
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'source_sheets', 'sandrock')
OUT = os.path.join(ROOT, 'assets', 'sandrock')
sys.path.insert(0, HERE)
import sandrock_names as N

FRINGE = 40      # 이 알파 미만은 번짐으로 보고 지움
SOLID = 230      # 이 알파 이상은 '진짜 색'
PAD = 4


def clean(rgba):
    a = rgba[:, :, 3].astype(np.int32)
    a[a < FRINGE] = 0
    solid = a >= SOLID
    if solid.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
        edge = (a > 0) & ~solid
        rgba[:, :, :3][edge] = rgba[:, :, :3][iy[edge], ix[edge]]
    rgba[:, :, 3] = a.astype(np.uint8)
    rgba[:, :, :3][a == 0] = 0
    return rgba


def blobs(rgba, expect, join=3):
    mask = rgba[:, :, 3] >= 80
    lab, n = ndimage.label(ndimage.binary_dilation(mask, iterations=join))
    objs = ndimage.find_objects(lab)
    areas = ndimage.sum(mask, lab, range(1, n + 1))
    items = [(objs[i], areas[i]) for i in range(n)]
    items.sort(key=lambda t: -t[1])
    big, small = items[:expect], items[expect:]
    if len(big) < expect:
        raise SystemExit(f'덩어리 {len(big)}개 < 이름표 {expect}개')
    # 큰 덩어리 중 가장 작은 것이 너무 작으면(부스러기를 그림으로 착각) 경고
    if big[-1][1] < 0.08 * big[0][1]:
        raise SystemExit(f'덩어리 크기가 고르지 않음: 최대 {big[0][1]:.0f}, 최소 {big[-1][1]:.0f}')
    boxes = [[s[0].start, s[0].stop, s[1].start, s[1].stop] for s, _ in big]
    # 작은 부스러기(반짝이 등)는 가장 가까운 덩어리에 합침
    for s, _ in small:
        cy, cx = (s[0].start + s[0].stop) / 2, (s[1].start + s[1].stop) / 2
        j = min(range(len(boxes)), key=lambda k: (cy - (boxes[k][0] + boxes[k][1]) / 2) ** 2 + (cx - (boxes[k][2] + boxes[k][3]) / 2) ** 2)
        b = boxes[j]
        b[0], b[1], b[2], b[3] = min(b[0], s[0].start), max(b[1], s[0].stop), min(b[2], s[1].start), max(b[3], s[1].stop)
    # 줄 나누기: 위쪽부터, 같은 줄 = 세로 중심 차이가 평균 높이의 절반 이하
    boxes.sort(key=lambda b: (b[0] + b[1]) / 2)
    hmean = np.mean([b[1] - b[0] for b in boxes])
    rows, cur = [], [boxes[0]]
    for b in boxes[1:]:
        if abs((b[0] + b[1]) / 2 - np.mean([(c[0] + c[1]) / 2 for c in cur])) < hmean * 0.5:
            cur.append(b)
        else:
            rows.append(cur); cur = [b]
    rows.append(cur)
    return [b for r in rows for b in sorted(r, key=lambda b: b[2])], [len(r) for r in rows]


def crop(rgba, b):
    h, w = rgba.shape[:2]
    y0, y1, x0, x1 = max(0, b[0] - PAD), min(h, b[1] + PAD), max(0, b[2] - PAD), min(w, b[3] + PAD)
    sub = rgba[y0:y1, x0:x1].copy()
    # 옆 그림의 침범 부분 없애기: 이 상자 밖에서 시작한 덩어리 제거
    m = sub[:, :, 3] > 0
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        objs = ndimage.find_objects(lab)
        for i, s in enumerate(sizes, 1):
            sl = objs[i - 1]
            touches = sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == sub.shape[0] or sl[1].stop == sub.shape[1]
            keep[i] = not (touches and s < 0.2 * sizes.max())
        sub[~keep[lab]] = 0
    return sub


manifest = {}


def save(kind, name, label, arr, src):
    d = os.path.join(OUT, kind); os.makedirs(d, exist_ok=True)
    ys, xs = np.nonzero(arr[:, :, 3])
    arr = arr[max(0, ys.min() - PAD):ys.max() + PAD + 1, max(0, xs.min() - PAD):xs.max() + PAD + 1]
    Image.fromarray(arr).save(os.path.join(d, name + '.png'), optimize=True)
    manifest[f'{kind}/{name}'] = dict(name=label, src=src, size=[arr.shape[1], arr.shape[0]])


def sheet(fname, kind, names, join=3):
    rgba = clean(np.array(Image.open(os.path.join(SRC, fname)).convert('RGBA')))
    boxes, rows = blobs(rgba, len(names), join)
    print(f'{fname}: {len(boxes)}개 {rows}')
    for (key, label), b in zip(names, boxes):
        save(kind, key, label, crop(rgba, b), fname)


def single(fname, kind, key, label):
    rgba = clean(np.array(Image.open(os.path.join(SRC, fname)).convert('RGBA')))
    save(kind, key, label, rgba, fname)


def recolor(src_key, dst_key, label, hue, s_mul, v_mul):
    """아이콘 색 바꾸기: 색상(0~255 기준)을 hue로 옮기고 채도·명도를 배율로 조정. 투명도는 그대로."""
    p = os.path.join(OUT, 'icons', src_key + '.png')
    im = Image.open(p).convert('RGBA')
    a = np.array(im)[:, :, 3]
    hsv = np.array(im.convert('RGB').convert('HSV')).astype(np.float32)
    sat = hsv[:, :, 1] > 40          # 회색 부분(하이라이트·그림자)은 색상만 살짝
    hsv[:, :, 0] = np.where(sat, hue, hsv[:, :, 0])
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * s_mul, 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * v_mul, 0, 255)
    out = Image.fromarray(hsv.astype(np.uint8), 'HSV').convert('RGB')
    out.putalpha(Image.fromarray(a))
    out.save(os.path.join(OUT, 'icons', dst_key + '.png'), optimize=True)
    manifest[f'icons/{dst_key}'] = dict(name=label, src=f'icons/{src_key} 색 변환', size=list(out.size))


def player():
    """루시에라: 3줄(정면/뒷면/옆면) x 5칸. 발 위치(아래 가운데)를 맞춘 같은 크기 칸으로 정렬."""
    fname = 'player_luciera.png'
    rgba = clean(np.array(Image.open(os.path.join(SRC, fname)).convert('RGBA')))
    boxes, rows = blobs(rgba, 15, join=2)
    print(f'{fname}: {rows}')
    if rows != [5, 5, 5]:
        raise SystemExit('루시에라 시트가 5x3이 아님')
    frames = [crop(rgba, b) for b in boxes]
    W = max(f.shape[1] for f in frames); H = max(f.shape[0] for f in frames)
    d = os.path.join(OUT, 'player'); os.makedirs(d, exist_ok=True)
    sheet_out = Image.new('RGBA', (W * 5, H * 3))
    for i, f in enumerate(frames):
        ys, xs = np.nonzero(f[:, :, 3])
        f = f[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        cell = Image.new('RGBA', (W, H))
        cell.paste(Image.fromarray(f), ((W - f.shape[1]) // 2, H - f.shape[0] - PAD))
        sheet_out.paste(cell, ((i % 5) * W, (i // 5) * H))
    sheet_out.save(os.path.join(d, 'luciera_walk.png'), optimize=True)
    manifest['player/luciera_walk'] = dict(name='루시에라 걷기(정면/뒷면/옆면 x5)', src=fname, size=[W * 5, H * 3], cell=[W, H])


if __name__ == '__main__':
    player()
    sheet('bld_sheet_8.png', 'buildings', N.BUILDINGS[:8])
    for i, (key, label) in enumerate(N.BUILDINGS[8:], 9):
        single(f'bld_{i:02d}.png', 'buildings', key, label)
    for i in range(5):
        sheet(f'npc_sheet_{i + 1}.png', 'npcs', N.NPCS[i * 5:i * 5 + 5])
    for i in range(6):
        sheet(f'station_sheet_{i + 1}.png', 'stations', N.STATIONS[i * 6:i * 6 + 6])
    for i in range(4):
        sheet(f'icon_sheet_{i + 1}.png', 'icons', N.ICONS[i * 40:i * 40 + 40])
    sheet('node_herb_v2.png', 'nodes', N.NODES_HERB)
    # 독버섯 군락은 1번째 버전(빨간 갓 = 아이콘과 같은 모양)
    sheet('node_herb_v1.png', 'nodes_alt', [(k + '_v1', l + '(1번째)') for k, l in N.NODES_HERB])
    for f, names in N.NODES.items():
        sheet(f, 'nodes', names)
    sheet('tools_axe_pick.png', 'tools', N.TOOLS)
    # 케인 확정(2026-10-07): 청동 주괴는 구리 주괴를 색 변환해 만든다. 놋쇠는 금·청동과 겹치지 않게 조정.
    #   금 = 밝고 진한 금빛(원본 그대로) / 청동 = 어두운 황갈(청동 도구 색) / 놋쇠 = 밝고 탁한 노란빛
    recolor('copper_ingot', 'bronze_ingot', '청동 주괴', hue=19, s_mul=1.00, v_mul=0.88)
    recolor('brass_ingot', 'brass_ingot', '놋쇠 주괴', hue=31, s_mul=0.70, v_mul=1.18)
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=1)
    print('완료:', len(manifest), '개')
