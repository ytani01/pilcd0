from PIL import Image, ImageDraw
import time
import itertools

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

def draw_robot_face(width, height, eye_state, mouth_state):
    """
    ロボットの顔をPILで描画する
    eye_state: "open", "half", "closed"
    mouth_state: "smile", "neutral", "sad"
    """
    img = Image.new("RGB", (width, height), (200, 220, 255))
    draw = ImageDraw.Draw(img)

    # 顔の枠（丸いロボットの頭）
    draw.ellipse((20, 20, width-20, height-20), fill=(180, 200, 240), outline=(0, 0, 0), width=3)

    # 目の位置
    eye_radius = 25
    left_eye_center = (width//3, height//3)
    right_eye_center = (2*width//3, height//3)

    # 目の描画（状態ごとに変化）
    def draw_eye(center, state):
        x, y = center
        if state == "open":
            draw.ellipse((x-eye_radius, y-eye_radius, x+eye_radius, y+eye_radius), fill=(255, 255, 255), outline=(0, 0, 0), width=3)
            draw.ellipse((x-10, y-10, x+10, y+10), fill=(0, 0, 0))
        elif state == "half":
            draw.rectangle((x-eye_radius, y-5, x+eye_radius, y+5), fill=(0, 0, 0))
        elif state == "closed":
            draw.line((x-eye_radius, y, x+eye_radius, y), fill=(0, 0, 0), width=4)

    draw_eye(left_eye_center, eye_state)
    draw_eye(right_eye_center, eye_state)

    # 口の描画（状態ごとに変化）
    mouth_top = height*2//3
    if mouth_state == "smile":
        draw.arc((width//3, mouth_top-20, 2*width//3, mouth_top+20), start=200, end=340, fill=(0, 0, 0), width=4)
    elif mouth_state == "neutral":
        draw.line((width//3, mouth_top, 2*width//3, mouth_top), fill=(0, 0, 0), width=4)
    elif mouth_state == "sad":
        draw.arc((width//3, mouth_top-10, 2*width//3, mouth_top+30), start=20, end=160, fill=(0, 0, 0), width=4)

    return img

def main():
    with ST7789V_Driver(speed_hz=40000000) as lcd:
        print("ロボットの顔アニメーション開始... Ctrl+C で終了してください。")

        # 表情の組み合わせ
        eye_states = ["open", "half", "closed"]
        mouth_states = ["smile", "neutral", "sad"]

        # itertoolsで組み合わせを順番にループ
        for eye_state, mouth_state in itertools.cycle([(e, m) for e in eye_states for m in mouth_states]):
            img = draw_robot_face(lcd.width, lcd.height, eye_state, mouth_state)
            pixel_bytes = pil_to_rgb565_bytes(img)

            lcd.set_window(0, 0, lcd.width - 1, lcd.height - 1)
            lcd.write_pixels(pixel_bytes)

            time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("終了しました。")
