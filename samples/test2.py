from PIL import Image, ImageDraw
import time
import random

from st7789v_driver import ST7789V_Driver

def main():
    with ST7789V_Driver(speed_hz=40000000) as lcd:
        print("アニメーション開始... Ctrl+C で終了してください。")
        try:
            import numpy
            print("numpyを検出しました。高速な描画が可能です。")
        except ImportError:
            print("警告: numpyがインストールされていません。描画が低速になります。")
            print("`pip install numpy` でパフォーマンスが向上します。")

        # ボールの初期位置と速度
        ball_x, ball_y = 50, 50
        dx, dy = 4, 3 # 速度を少し上げる
        ball_radius = 20
        
        last_time = time.time()
        frame_count = 0

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

            # PIL ImageをLCDに送信
            lcd.display(img)
            
            frame_count += 1
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                print(f"FPS: {fps:.2f}")
                frame_count = 0
                last_time = current_time

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n終了しました。")