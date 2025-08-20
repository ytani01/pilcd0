# -*- coding: utf-8 -*-
"""
Pillow(PIL)とnumpyを使ったアニメーションのための、再利用可能なユーティリティ群。

このライブラリは、ST7789VのようなSPI接続のディスプレイ上で、
効率的なアニメーションを実現するための、汎用的なクラスと関数を提供します。
"""
import time
from PIL import Image, ImageDraw, ImageFont

try:
    import numpy as np
except ImportError:
    raise ImportError("このライブラリのパフォーマンスにはnumpyが不可欠です。'pip install numpy'でインストールしてください。")

# --- 汎用ユーティリティ関数 ---

def pil_to_rgb565_bytes(img):
    """PIL.Image → RGB565のバイト列に変換 (numpyを使った高速版)"""
    np_img = np.array(img, dtype=np.uint8)
    r = (np_img[:, :, 0] >> 3).astype(np.uint16)
    g = (np_img[:, :, 1] >> 2).astype(np.uint16)
    b = (np_img[:, :, 2] >> 3).astype(np.uint16)
    rgb565 = (r << 11) | (g << 5) | b
    return rgb565.byteswap().tobytes()

def merge_bboxes(bbox1, bbox2):
    """2つのバウンディングボックスをマージして、両方を含む最小のボックスを返す"""
    if not bbox1: return bbox2
    if not bbox2: return bbox1
    return (
        min(bbox1[0], bbox2[0]),
        min(bbox1[1], bbox2[1]),
        max(bbox1[2], bbox2[2]),
        max(bbox1[3], bbox2[3]),
    )

# --- 汎用コンポーネントクラス ---

class Ball:
    """画面内を反射して移動するボールの状態と振る舞いを管理するクラス"""
    def __init__(self, x, y, radius, speed_x, speed_y, fill_color, outline_color):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.speed_x = float(speed_x)
        self.speed_y = float(speed_y)
        self.fill_color = fill_color
        self.outline_color = outline_color
        self.prev_bbox = None

    def update_position(self, delta_t, screen_width, screen_height):
        """デルタタイムに基づいてボールの位置を更新し、壁での反射を処理する"""
        self.x += self.speed_x * delta_t
        self.y += self.speed_y * delta_t

        if self.x - self.radius < 0:
            self.x = self.radius
            self.speed_x = -self.speed_x
        if self.x + self.radius >= screen_width:
            self.x = screen_width - self.radius - 1
            self.speed_x = -self.speed_x
        if self.y - self.radius < 0:
            self.y = self.radius
            self.speed_y = -self.speed_y
        if self.y + self.radius >= screen_height:
            self.y = screen_height - self.radius - 1
            self.speed_y = -self.speed_y

    def get_bbox(self):
        """現在のボールの位置からバウンディングボックスを計算する"""
        return (
            int(self.x - self.radius), int(self.y - self.radius),
            int(self.x + self.radius), int(self.y + self.radius)
        )

    def draw(self, lcd, bg_img):
        """差分描画ロジックを実行する"""
        curr_bbox = self.get_bbox()
        update_bbox = merge_bboxes(self.prev_bbox, curr_bbox)
        
        if update_bbox:
            update_bbox = (
                max(0, update_bbox[0] - 1), max(0, update_bbox[1] - 1),
                min(lcd.width, update_bbox[2] + 1), min(lcd.height, update_bbox[3] + 1),
            )
            update_img = bg_img.crop(update_bbox)
            draw = ImageDraw.Draw(update_img)
            draw_x = curr_bbox[0] - update_bbox[0]
            draw_y = curr_bbox[1] - update_bbox[1]
            draw.ellipse(
                (draw_x, draw_y, draw_x + self.radius * 2, draw_y + self.radius * 2),
                fill=self.fill_color, outline=self.outline_color
            )
            pixel_bytes = pil_to_rgb565_bytes(update_img)
            lcd.set_window(update_bbox[0], update_bbox[1], update_bbox[2] - 1, update_bbox[3] - 1)
            lcd.write_pixels(pixel_bytes)

        self.prev_bbox = curr_bbox

class FpsCounter:
    """FPSの計算と描画を管理するクラス"""
    def __init__(self, bg_img, font_path, font_size, text_color, update_interval=0.25, padding=5):
        try:
            self.font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"警告: '{font_path}' が見つかりません。デフォルトフォントを使用します。")
            self.font = ImageFont.load_default()

        self.text_color = text_color
        self.update_interval = update_interval
        
        pos = (padding, padding)
        base_bbox = ImageDraw.Draw(bg_img).textbbox((0,0), "FPS: 999.9", font=self.font)
        box_width = base_bbox[2] - base_bbox[0] + (padding * 2)
        box_height = base_bbox[3] - base_bbox[1] + (padding * 2)
        
        self.bbox = (pos[0], pos[1], pos[0] + box_width, pos[1] + box_height)
        self.draw_offset = (padding - base_bbox[0], padding - base_bbox[1])

        self.frame_count = 0
        self.last_update_time = time.time()
        self.bg_crop = bg_img.crop(self.bbox)

    def update_and_draw(self, lcd):
        """FPSを計算し、更新タイミングであれば描画する"""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_update_time

        if elapsed >= self.update_interval:
            fps = self.frame_count / elapsed
            fps_text = f"FPS: {fps:.1f}"
            
            text_img = self.bg_crop.copy()
            draw = ImageDraw.Draw(text_img)
            draw.text(self.draw_offset, fps_text, font=self.font, fill=self.text_color)
            
            pixel_bytes = pil_to_rgb565_bytes(text_img)
            lcd.set_window(self.bbox[0], self.bbox[1], self.bbox[2] - 1, self.bbox[3] - 1)
            lcd.write_pixels(pixel_bytes)
            
            self.frame_count = 0
            self.last_update_time = current_time
