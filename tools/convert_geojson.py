#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoJSON → BlueOS 离线地图数据 转换工具

将标准 GeoJSON（LineString / Polygon / Point）转换为
src/pages/Map/mapdata.js 所需的紧凑矢量格式，用于替换示例数据。

用法：
    python3 tools/convert_geojson.py <input.geojson> [output.js] [--center lat,lng] [--zoom z]

GeoJSON 约定（通过 properties 字段映射）：
    - 道路   : Feature.geometry.type == LineString
                properties.kind: highway(主干道)/street(一般道路)/rail(轨道)，默认 street
    - 水面   : Feature.geometry.type == Polygon（闭合，渲染时填充）
    - POI    : Feature.geometry.type == Point
                properties.type: metro/school/office/gate/mall/park/hospital/food 等
输出文件的坐标一律为 [纬度, 经度]（WGS-84）。
"""
import json
import sys
import argparse


def coord_to_ll(c):
    """GeoJSON 坐标为 [lng, lat]，转换为内部 [lat, lng]"""
    lng, lat = float(c[0]), float(c[1])
    return [round(lat, 6), round(lng, 6)]


def geom_points(geom):
    """提取几何的所有坐标点（用于计算包围盒/中心）"""
    pts = []
    t = geom['type']
    if t == 'Point':
        pts.append(coord_to_ll(geom['coordinates']))
    elif t == 'LineString':
        pts.extend(coord_to_ll(c) for c in geom['coordinates'])
    elif t == 'Polygon':
        for ring in geom['coordinates']:
            pts.extend(coord_to_ll(c) for c in ring)
    elif t == 'MultiLineString':
        for line in geom['coordinates']:
            pts.extend(coord_to_ll(c) for c in line)
    elif t == 'MultiPolygon':
        for poly in geom['coordinates']:
            for ring in poly:
                pts.extend(coord_to_ll(c) for c in ring)
    return pts


def main():
    ap = argparse.ArgumentParser(description='GeoJSON → BlueOS 离线地图数据')
    ap.add_argument('input', help='输入 GeoJSON 文件路径')
    ap.add_argument('output', nargs='?', default=None,
                    help='输出 js 文件路径（默认写入 src/pages/Map/mapdata.js 同级 mapdata.generated.js）')
    ap.add_argument('--center', default=None, help='地图中心 lat,lng（默认取数据几何中心）')
    ap.add_argument('--name', default='离线地图区域', help='地图区域名称')
    ap.add_argument('--zoom', type=float, default=15.0, help='初始缩放级别（默认 15）')
    args = ap.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        gj = json.load(f)

    if gj.get('type') != 'FeatureCollection':
        sys.exit('错误：仅支持 FeatureCollection 类型的 GeoJSON')

    roads, waters, pois = [], [], []
    all_pts = []

    for feat in gj.get('features', []):
        geom = feat.get('geometry') or {}
        props = feat.get('properties') or {}
        name = props.get('name') or props.get('title') or props.get('标签') or ''
        t = geom.get('type')
        pts = geom_points(geom)
        all_pts.extend(pts)

        if t == 'Point':
            lat, lng = pts[0]
            pois.append({'name': name, 'lat': lat, 'lng': lng,
                         'type': props.get('type', 'park')})
        elif t in ('LineString', 'MultiLineString'):
            lines = [geom['coordinates']] if t == 'LineString' else geom['coordinates']
            for line in lines:
                roads.append({
                    'type': props.get('kind', 'street'),
                    'name': name,
                    'points': [coord_to_ll(c) for c in line]
                })
        elif t in ('Polygon', 'MultiPolygon'):
            polys = [geom['coordinates']] if t == 'Polygon' else geom['coordinates']
            for poly in polys:
                ring = poly[0] if poly else []
                if ring:
                    waters.append({'name': name, 'points': [coord_to_ll(c) for c in ring]})

    if not all_pts:
        sys.exit('错误：输入数据中没有可识别的要素')

    lats = [p[0] for p in all_pts]
    lngs = [p[1] for p in all_pts]
    if args.center:
        clat, clng = [float(x) for x in args.center.split(',')]
    else:
        clat = (max(lats) + min(lats)) / 2
        clng = (max(lngs) + min(lngs)) / 2

    out = {
        'name': args.name,
        'center': [round(clat, 6), round(clng, 6)],
        'zoom': args.zoom,
        'minZoom': 12.5,
        'maxZoom': 18.5,
        'roads': roads,
        'waters': waters,
        'pois': pois,
    }

    out_path = args.output or 'src/pages/Map/mapdata.generated.js'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('/**\n * 本文件由 tools/convert_geojson.py 自动生成，请勿手工修改。\n */\n')
        f.write('export default ')
        f.write(json.dumps(out, ensure_ascii=False, indent=2))
        f.write('\n')

    print(f'完成：roads={len(roads)} waters={len(waters)} pois={len(pois)}')
    print(f'数据范围: lat {min(lats):.5f}~{max(lats):.5f} lng {min(lngs):.5f}~{max(lngs):.5f}')
    print(f'地图中心: {clat:.5f},{clng:.5f}  →  输出: {out_path}')


if __name__ == '__main__':
    main()
