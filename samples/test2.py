from PIL import Image, ImageDraw
import time
import random

from st7789v_driver import ST7789V_Driver

def pil_to_rgb565_bytes(img):
    """PIL.Image → RGB565のバイト列に変換"""
    pixel_data = []
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b = img.getpixel((x, y))
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixel_data.append(rgb565 >> 8)
            pixel_data.append(rgb565 & 0xFF)
    return bytearray(pixel_data)

def main():
    with ST7789V_Driver(speed_hz=40000000) as lcd:
        print("アニメーション開始... Ctrl+C で終了してください。")

        # ボールの初期位置と速度
        ball_x, ball_y = 50, 50
        dx, dy = 3, 2
        ball_radius = 20

        while True:
            # フレーム画像作成
            img = Image.new("RGB", (lcd.width, lcd.height), (0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 背景にグラデーション風の色
            for y in range(lcd.height):
                color = (y % 256, (y*2) % 256, (y*3) % 256)
                draw.line((0, y, lcd.width, y), fill=color)

            # ボールを描画
            draw.ellipse(
                (ball_x - ball_radius, ball_y - ball_radius,
                 ball_x + ball_radius, ball_y + ball_radius),
                fill=(255, 255, 0), outline=(255, 255, 255)
            )

            # ボールの位置更新
            ball_x += dx
            ball_y += dy

            # 壁で反射
            if ball_x - ball_radius < 0 or ball_x + ball_radius >= lcd.width:
                dx = -dx
            if ball_y - ball_radius < 0 or ball_y + ball_radius >= lcd.height:
                dy = -dy

            # PIL → RGB565 バイト列変換
            pixel_bytes = pil_to_rgb565_bytes(img)

            # LCDに送信
            lcd.set_window(0, 0, lcd.width - 1, lcd.height - 1)
            lcd.write_pixels(pixel_bytes)

            # 少し待つ（fps調整）
            time.sleep(0.03)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("終了しました。")
