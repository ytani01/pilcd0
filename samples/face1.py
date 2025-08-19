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

def draw_robot_face(width, height, expression="smile"):
    """
    ロボットの顔を描画
    expression: "smile", "wink", "surprised", "sad"
    """
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # --- 本体 ---
    margin = 40
    body_rect = (margin, margin, width-margin, height-margin)
    draw.rounded_rectangle(body_rect, radius=40, fill=(200, 210, 230), outline=(80, 90, 100), width=6)

    # --- 耳 ---
    ear_w = 30
    ear_h = 80
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

    # --- 目と口 ---
    eye_r = 25
    left_eye = (width//3-eye_r, height//3-eye_r, width//3+eye_r, height//3+eye_r)
    right_eye = (2*width//3-eye_r, height//3-eye_r, 2*width//3+eye_r, height//3+eye_r)

    if expression == "smile":
        draw.ellipse(left_eye, fill=(0, 0, 0))
        draw.ellipse(right_eye, fill=(0, 0, 0))
        draw.arc((width//3, height//2, 2*width//3, height//2+60), 0, 180, fill=(0, 0, 0), width=6)

    elif expression == "wink":
        draw.line((left_eye[0], (left_eye[1]+left_eye[3])//2, left_eye[2], (left_eye[1]+left_eye[3])//2), fill=(0,0,0), width=6)
        draw.ellipse(right_eye, fill=(0, 0, 0))
        draw.arc((width//3, height//2, 2*width//3, height//2+60), 0, 180, fill=(0, 0, 0), width=6)

    elif expression == "surprised":
        draw.ellipse(left_eye, fill=(0, 0, 0))
        draw.ellipse(right_eye, fill=(0, 0, 0))
        draw.ellipse((width//2-25, height//2+30, width//2+25, height//2+80), outline=(0, 0, 0), width=6)

    elif expression == "sad":
        draw.ellipse(left_eye, fill=(0, 0, 0))
        draw.ellipse(right_eye, fill=(0, 0, 0))
        draw.arc((width//3, height//2+20, 2*width//3, height//2+70), 180, 360, fill=(0, 0, 0), width=6)

    return img

def main():
    with ST7789V_Driver(speed_hz=40000000) as lcd:
        expressions = ["smile", "wink", "surprised", "sad"]

        for expr in itertools.cycle(expressions):
            img = draw_robot_face(lcd.width, lcd.height, expr)
            pixel_bytes = pil_to_rgb565_bytes(img)

            lcd.set_window(0, 0, lcd.width - 1, lcd.height - 1)
            lcd.write_pixels(pixel_bytes)

            time.sleep(1.0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("終了しました。")

