#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
省级 GeoJSON → BlueOS 离线地图数据 转换工具

将阿里 DataV 行政区划 GeoJSON（FeatureCollection，每个 Feature 为一个地级市 MultiPolygon）
转换为 mapdata.js 中 regions 数组所需条目。

特性：
  - Ramer-Douglas-Peucker 多边形简化，控制数据体积
  - 自动计算省份中心与适配 466px 圆屏的初始 zoom
  - 城市边界作为 regions（陆地填充 + 描边）
  - 地级市中心作为 POI（type=city）
  - 输出 [lat, lng] 坐标（WGS-84）

用法：
    python3 tools/convert_province.py <input.geojson> <id> [--name 省] [--tolerance 0.005]
"""
import json
import sys
import math
import argparse


def rdp(points, tolerance):
    """Ramer-Douglas-Peucker 折线简化（points: [[lat,lng],...]）"""
    if len(points) < 3:
        return points

    def perp_dist(p, a, b):
        if a[0] == b[0] and a[1] == b[1]:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        dx, dy = b[1] - a[1], b[0] - a[0]
        norm = math.hypot(dx, dy)
        return abs(dy * (p[1] - a[1]) - dx * (p[0] - a[0])) / norm

    keep = [False] * len(points)
    keep[0] = keep[-1] = True

    def recurse(s, e):
        maxd, idx = 0, -1
        for i in range(s + 1, e):
            d = perp_dist(points[i], points[s], points[e])
            if d > maxd:
                maxd, idx = d, i
        if maxd > tolerance and idx > 0:
            keep[idx] = True
            recurse(s, idx)
            recurse(idx, e)

    recurse(0, len(points) - 1)
    return [points[i] for i in range(len(points)) if keep[i]]


def ring_area(pts):
    """近似多边形面积（球面，单位度²）"""
    s = 0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        s += pts[i][1] * pts[j][0] - pts[j][1] * pts[i][0]
    return abs(s) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', help='输入 GeoJSON')
    ap.add_argument('rid', help='区域 id，如 jiangsu')
    ap.add_argument('--name', default=None, help='区域显示名')
    ap.add_argument('--tolerance', type=float, default=0.005,
                    help='RDP 简化容差（度），越大越精简')
    args = ap.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        gj = json.load(f)

    regions = []
    pois = []
    all_lats, all_lngs = [], []

    for feat in gj.get('features', []):
        props = feat.get('properties') or {}
        geom = feat.get('geometry') or {}
        name = props.get('name', '')
        center = props.get('center') or props.get('centroid')

        # 取最大环作为城市外边界（MultiPolygon 选面积最大的）
        rings = []
        if geom.get('type') == 'Polygon':
            rings = [geom['coordinates'][0]]
        elif geom.get('type') == 'MultiPolygon':
            for poly in geom['coordinates']:
                if poly and poly[0]:
                    rings.append(poly[0])

        if not rings:
            continue

        # 选面积最大的环
        best_ring = max(rings, key=ring_area)
        pts = [[float(c[1]), float(c[0])] for c in best_ring]  # [lat,lng]
        all_lats.extend(p[0] for p in pts)
        all_lngs.extend(p[1] for p in pts)

        # 闭合环去尾
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]

        simplified = rdp(pts, args.tolerance)

        regions.append({
            'name': name,
            'points': [[round(p[0], 5), round(p[1], 5)] for p in simplified]
        })

        # 城市 POI
        if center and len(center) >= 2:
            pois.append({
                'name': name,
                'lat': round(float(center[1]), 5),
                'lng': round(float(center[0]), 5),
                'type': 'city'
            })

    if not regions:
        sys.exit('错误：未提取到任何城市边界')

    clat = (max(all_lats) + min(all_lats)) / 2
    clng = (max(all_lngs) + min(all_lngs)) / 2

    # 计算 466px 圆屏适配 zoom：以省份跨度较大的方向为准
    PX_M_BASE = 156543.03392
    M_PER_DEG = 111320
    lat_span = max(all_lats) - min(all_lats)  # 度
    lng_span = max(all_lngs) - min(all_lngs)  # 度
    # 转米
    cos_lat = math.cos(clat * math.pi / 180)
    span_m = max(lat_span * M_PER_DEG, lng_span * M_PER_DEG * cos_lat)
    # 466px 留 80% 余量 → m/px
    m_per_px = span_m / (466 * 0.8)
    # zoom: m/px = PX_M_BASE * cosLat / 2^zoom
    zoom = math.log2(PX_M_BASE * cos_lat / m_per_px)
    zoom = round(zoom, 2)

    out = {
        'id': args.rid,
        'name': args.name or args.rid,
        'center': [round(clat, 5), round(clng, 5)],
        'zoom': zoom,
        'minZoom': round(max(zoom - 2, 4), 2),
        'maxZoom': round(zoom + 3, 2),
        'regions': regions,
        'roads': [],
        'waters': [],
        'pois': pois,
    }

    # 输出到 stdout，供组装
    print(json.dumps(out, ensure_ascii=False))
    sys.stderr.write(
        f'[{args.rid}] 城市数={len(regions)} POI={len(pois)} '
        f'zoom={zoom} center=[{clat:.4f},{clng:.4f}]\n'
    )


if __name__ == '__main__':
    main()
