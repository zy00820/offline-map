#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组装 mapdata.js：合并北京（街道级）+ 江苏/四川（省级）多区域数据。
读取 /tmp/jiangsu.json、/tmp/sichuan.json 与现有北京数据，输出 src/pages/Map/mapdata.js。
"""
import json

# 北京·五道口（街道级，沿用原示例数据）
beijing = {
    "id": "beijing",
    "name": "北京·五道口",
    "center": [39.996, 116.334],
    "zoom": 15.2,
    "minZoom": 12.5,
    "maxZoom": 18.5,
    "regions": [],
    "roads": [
        {"type": "highway", "name": "成府路", "points": [
            [39.9946, 116.3232], [39.9941, 116.327], [39.9935, 116.3306],
            [39.9929, 116.334], [39.9926, 116.337], [39.9923, 116.34],
            [39.992, 116.3432]
        ]},
        {"type": "street", "name": "荷清路", "points": [
            [40.0045, 116.3298], [40.0, 116.33], [39.996, 116.3303],
            [39.993, 116.3306]
        ]},
        {"type": "highway", "name": "清华路", "points": [
            [40.0043, 116.3232], [40.0041, 116.328], [40.0036, 116.332],
            [40.003, 116.3358]
        ]},
        {"type": "highway", "name": "中关村北大街", "points": [
            [40.0065, 116.3222], [40.002, 116.3232], [39.9978, 116.323],
            [39.9932, 116.3226]
        ]},
        {"type": "street", "name": "双清路", "points": [
            [40.0068, 116.343], [40.0032, 116.3408], [39.9992, 116.3388],
            [39.9955, 116.337]
        ]},
        {"type": "street", "name": "清华东路", "points": [
            [40.0029, 116.3258], [40.003, 116.331], [40.0031, 116.335],
            [40.0032, 116.3392]
        ]},
        {"type": "street", "name": "清华南门路", "points": [
            [39.9992, 116.3268], [39.9995, 116.3312], [39.9998, 116.335],
            [40.0001, 116.3388]
        ]},
        {"type": "rail", "name": "京张铁路(地铁13号线)", "points": [
            [40.0075, 116.3392], [40.003, 116.3375], [39.9988, 116.3356],
            [39.995, 116.3338]
        ]}
    ],
    "waters": [
        {"name": "清华荷塘", "points": [
            [40.0018, 116.3266], [40.0018, 116.3288],
            [40.0004, 116.3288], [40.0004, 116.3266]
        ]}
    ],
    "pois": [
        {"name": "五道口地铁站", "lat": 39.9925, "lng": 116.3377, "type": "metro"},
        {"name": "清华大学", "lat": 40.0038, "lng": 116.3262, "type": "school"},
        {"name": "清华科技园", "lat": 39.9998, "lng": 116.3302, "type": "office"},
        {"name": "清华西门", "lat": 40.0029, "lng": 116.3234, "type": "gate"},
        {"name": "五道口购物中心", "lat": 39.9923, "lng": 116.3392, "type": "mall"},
        {"name": "京张铁路遗址公园", "lat": 39.9982, "lng": 116.3358, "type": "park"},
        {"name": "清华同方科技广场", "lat": 39.9989, "lng": 116.3282, "type": "office"},
        {"name": "东源大厦", "lat": 39.9966, "lng": 116.3382, "type": "office"}
    ]
}

with open('/tmp/jiangsu.json', 'r', encoding='utf-8') as f:
    jiangsu = json.load(f)
with open('/tmp/sichuan.json', 'r', encoding='utf-8') as f:
    sichuan = json.load(f)

out = {"regions": [beijing, jiangsu, sichuan]}

with open('/workspace/offline-map/src/pages/Map/mapdata.js', 'w', encoding='utf-8') as f:
    f.write('/**\n')
    f.write(' * 离线矢量地图数据（多区域：北京 / 江苏 / 四川）\n')
    f.write(' *\n')
    f.write(' * 坐标系：WGS-84，单位为度，[纬度, 经度]（即 [lat, lng]）。\n')
    f.write(' * 数据完全内置在应用包中，渲染过程不依赖任何网络请求，可完全离线使用。\n')
    f.write(' *\n')
    f.write(' * 结构说明（每个区域对象）：\n')
    f.write(' *   - id      : 区域唯一标识\n')
    f.write(' *   - name    : 区域显示名称\n')
    f.write(' *   - center  : 地图中心 [lat, lng]\n')
    f.write(' *   - zoom    : 初始缩放（等效 Web 墨卡托 z 值）\n')
    f.write(' *   - regions : 行政区边界多边形（地级市，省级地图用）；街道级为空数组\n')
    f.write(' *   - roads   : 道路折线（街道级地图用）；省级为空数组\n')
    f.write(' *   - waters  : 水面多边形（街道级地图用）；省级为空数组\n')
    f.write(' *   - pois    : 兴趣点；街道级为地铁/学校等，省级为地级市中心\n')
    f.write(' */\n')
    f.write('export default ')
    f.write(json.dumps(out, ensure_ascii=False, indent=2))
    f.write('\n')

print(f'完成：{len(out["regions"])} 个区域')
for r in out['regions']:
    print(f"  - {r['id']}: {r['name']} zoom={r['zoom']} "
          f"regions={len(r['regions'])} roads={len(r['roads'])} pois={len(r['pois'])}")
