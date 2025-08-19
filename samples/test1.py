from PIL import Image, ImageDraw, ImageFont
import time

# ST7789Vドライバをインポート
from st7789v_driver import ST7789V_Driver

def main():
    # LCDを初期化（デフォルトで 320x240 横型）
    with ST7789V_Driver(speed_hz=40000000) as lcd:
        print("初期化完了。PILでグラフィック描画開始...")

        # PILのImageオブジェクト作成 (RGB, 320x240)
        img = Image.new("RGB", (lcd.width, lcd.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 背景を塗り分け
        draw.rectangle((0, 0, 159, 239), fill=(0, 0, 128))   # 左半分を青
        draw.rectangle((160, 0, 319, 239), fill=(0, 128, 0)) # 右半分を緑

        # 円を描画
        draw.ellipse((100, 60, 220, 180), fill=(255, 0, 0), outline=(255, 255, 255))

        # テキストを描画
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        except:
            font = ImageFont.load_default()
        draw.text((10, 10), "Hello ST7789V!", font=font, fill=(255, 255, 0))

        # PILイメージをRGB565のバイト列に変換
        pixel_data = []
        for y in range(lcd.height):
            for x in range(lcd.width):
                r, g, b = img.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixel_data.append(rgb565 >> 8)
                pixel_data.append(rgb565 & 0xFF)
        pixel_bytes = bytearray(pixel_data)

        # LCDに転送
        lcd.set_window(0, 0, lcd.width - 1, lcd.height - 1)
        lcd.write_pixels(pixel_bytes)

        print("描画完了。3秒後に終了します。")
        time.sleep(3)

if __name__ == "__main__":
    main()
