from PIL import Image, ImageDraw
import time
import math

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

def draw_robot_face(width, height, eye_open=1.0, mouth_curve=0.0):
    """
    ロボットの顔を描画する
    :param eye_open: 目の開き具合 (0=閉じる, 1=全開)
    :param mouth_curve: 口の曲がり具合 (-1=悲しい, 0=無表情, 1=笑顔)
    """
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # --- 本体 ---
    margin = 40
    body_rect = (margin, margin, width-margin, height-margin)
    draw.rounded_rectangle(body_rect, radius=40, fill=(200, 210, 230), outline=(80, 90, 100), width=6)

    # --- 耳 ---
    ear_w, ear_h = 30, 80
    draw.rounded_rectangle((margin-ear_w, height//2-ear_h//2, margin, height//2+ear_h//2),
                           radius=10, fill=(150, 180, 220), outline=(80, 90, 100), width=4)
    draw.rounded_rectangle((width-margin, height//2-ear_h//2, width-margin+ear_w, height//2+ear_h//2),
                           radius=10, fill=(150, 180, 220), outline=(80, 90, 100), width=4)

    # --- アンテナ ---
    draw.line((width//2, margin-20, width//2, margin), fill=(80, 90, 100), width=6)
    draw.ellipse((width//2-15, margin-35, width//2+15, margin-5), fill=(180, 200, 220), outline=(80, 90, 100), width=4)

    # --- 頬の赤み ---
    cheek_r = 20
    draw.ellipse((width//3-40, height//2+30, width//3-40+cheek_r*2, height//2+30+cheek_r*2),
                 fill=(255, 180, 180))
    draw.ellipse((2*width//3-40, height//2+30, 2*width//3-40+cheek_r*2, height//2+30+cheek_r*2),
                 fill=(255, 180, 180))

    # --- 目 ---
    eye_r = 25
    left_eye_c = (width//3, height//3)
    right_eye_c = (2*width//3, height//3)

    def draw_eye(center, open_ratio):
        x, y = center
        h = int(eye_r * open_ratio)
        if h < 3:  # ほぼ閉じているとき
            draw.line((x-eye_r, y, x+eye_r, y), fill=(0, 0, 0), width=4)
        else:
            draw.ellipse((x-eye_r, y-h, x+eye_r, y+h), fill=(0, 0, 0))

    draw_eye(left_eye_c, eye_open)
    draw_eye(right_eye_c, eye_open)

    # --- 口 ---
    mouth_top = height*2//3
    curve = int(40 * mouth_curve)  # -40〜+40 ピクセルでカーブ
    draw.arc((width//3, mouth_top-20-curve, 2*width//3, mouth_top+20+curve),
             start=0, end=180, fill=(0, 0, 0), width=6)

    return img

def main():
    with ST7789V_Driver(speed_hz=40000000) as lcd:
        print("ロボットの顔アニメーション開始... Ctrl+C で終了してください。")

        t = 0
        while True:
            # 目の開閉: sin波で自然な瞬き
            eye_open = (math.sin(t) + 1) / 2  # 0〜1

            # 口の表情: ゆっくり -1〜1 を往復
            mouth_curve = math.sin(t/3)

            # 描画
            img = draw_robot_face(lcd.width, lcd.height, eye_open=eye_open, mouth_curve=mouth_curve)
            pixel_bytes = pil_to_rgb565_bytes(img)

            lcd.set_window(0, 0, lcd.width - 1, lcd.height - 1)
            lcd.write_pixels(pixel_bytes)

            time.sleep(0.05)
            t += 0.2

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("終了しました。")
