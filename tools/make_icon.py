#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 BlueOS 应用图标（114x114 PNG，圆角，深色底 + 蓝色地图定位针）。
仅使用 Python 标准库（zlib + struct）直接写 PNG，无第三方依赖。

用法：python3 tools/make_icon.py
输出：src/assets/images/icon.png
"""
import struct
import zlib
import os

SIZE = 114
CORNER = 24  # 圆角半径


def in_rounded_rect(x, y, r):
    """判断 (x,y) 是否在左上角 (0,0) 右下角 (SIZE,SIZE) 的圆角矩形内"""
    cx = min(max(x, r), SIZE - r)
    cy = min(max(y, r), SIZE - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_circle(x, y, cx, cy, r):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_triangle(x, y, a, b, c):
    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    d1 = sign((x, y), a, b)
    d2 = sign((x, y), b, c)
    d3 = sign((x, y), c, a)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def px_color(x, y):
    """返回 (r,g,b,a)"""
    if not in_rounded_rect(x, y, CORNER):
        return (0, 0, 0, 0)  # 圆角外透明

    # 定位针：圆形头部 + 三角尾部
    head_cx, head_cy, head_r = 57, 45, 25
    if in_circle(x, y, head_cx, head_cy, head_r):
        # 内部白色圆点
        if in_circle(x, y, head_cx, head_cy, 9):
            return (255, 255, 255, 255)
        return (76, 195, 255, 255)  # #4cc3ff
    if in_triangle(x, y, (head_cx - 11, head_cy + 22), (head_cx + 11, head_cy + 22), (head_cx, head_cy + 64)):
        return (76, 195, 255, 255)
    return (10, 14, 20, 255)  # #0a0e14 底


def chunk(tag, data):
    c = tag + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)


def main():
    rows = []
    for y in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            r, g, b, a = px_color(x, y)
            row += bytes((r, g, b, a))
        rows.append(bytes(row))

    raw = b''.join(b'\x00' + r for r in rows)  # 每行前加 filter 0
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9))
    png += chunk(b'IEND', b'')

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'assets', 'images', 'icon.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(png)
    print('已生成:', os.path.abspath(out), os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    main()
