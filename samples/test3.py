# -*- coding: utf-8 -*-
"""
ST7789Vディスプレイで動作する、物理ベースのアニメーションデモ。

このスクリプトは、シンプルなボールのアニメーションを通じて、
組込み環境やシングルボードコンピュータで滑らかなグラフィックスを
実現するための、以下の主要なテクニックを実装しています。

1.  **numpyによる高速ピクセル変換:**
    PILのImageオブジェクトからLCD用のRGB565形式への変換を、
    numpyのベクトル化処理を用いて高速に実行します。

2.  **差分描画 (ダーティ矩形):**
    毎フレーム画面全体を更新するのではなく、ボールの移動によって変化が
    あった領域（ダーティ矩形）だけを特定し、その最小限の範囲のみを
    LCDに転送することで、データ転送量を劇的に削減します。

3.  **デルタタイムによる物理更新:**
    アニメーションの速度をフレームレートから独立させます。
    これにより、処理負荷が変動しても、ボールは常に人間が見て
    一定の速度で動くようになります。

4.  **フレームレート制限 (FPS Capping):**
    CPUリソースを100%使い切るのを防ぎ、指定したフレームレート
    （例: 30 FPS）を維持するように意図的に待機時間を挿入します。
    これにより、システムの負荷を軽減し、安定した動作を実現します。
"""
import time
from PIL import Image, ImageDraw, ImageFont

try:
    import numpy as np
except ImportError:
    print("エラー: numpy がインストールされていません。")
    print("このスクリプトのパフォーマンスには numpy が不可欠です。")
    print("コマンド: pip install numpy")
    exit()

from st7789v_driver import ST7789V_Driver

# --- 設定クラス ---
class CONFIG:
    """アニメーションの挙動を調整するための設定値"""
    # ディスプレイ設定
    SPI_SPEED_HZ = 16000000  # SPIクロック周波数

    # パフォーマンス設定
    TARGET_FPS = 30.0  # 目標フレームレート

    # ボールの物理設定
    BALL_RADIUS = 20
    BALL_INITIAL_SPEED_X = 300.0  # 横方向の速度 (ピクセル/秒)
    BALL_INITIAL_SPEED_Y = 200.0  # 縦方向の速度 (ピクセル/秒)

    # 描画設定
    BALL_FILL_COLOR = (255, 255, 0)
    BALL_OUTLINE_COLOR = (255, 255, 255)
    
    # FPSカウンター設定
    FPS_FONT_PATH = "Firge-Regular.ttf"
    FPS_FONT_SIZE = 50
    FPS_TEXT_COLOR = (255, 255, 255)
    FPS_UPDATE_INTERVAL = 0.2  # FPS表示の更新間隔 (秒)
    FPS_AREA_PADDING = 5      # FPS表示領域の余白

# --- ヘルパー関数 ---
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

# --- 描画オブジェクトクラス ---
class Ball:
    """ボールの状態と振る舞いを管理するクラス"""
    def __init__(self, x, y, radius, speed_x, speed_y):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.speed_x = float(speed_x)
        self.speed_y = float(speed_y)
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
        
        # 前のフレームと現在のフレームの描画範囲をマージ
        update_bbox = merge_bboxes(self.prev_bbox, curr_bbox)
        
        if update_bbox:
            # 安全マージンを追加して、輪郭線の残像を防ぐ
            update_bbox = (
                max(0, update_bbox[0] - 1), max(0, update_bbox[1] - 1),
                min(lcd.width, update_bbox[2] + 1), min(lcd.height, update_bbox[3] + 1),
            )
            
            # 描画処理
            update_img = bg_img.crop(update_bbox)
            draw = ImageDraw.Draw(update_img)
            
            # 更新領域内の相対座標にボールを描画
            draw_x = curr_bbox[0] - update_bbox[0]
            draw_y = curr_bbox[1] - update_bbox[1]
            draw.ellipse(
                (draw_x, draw_y, draw_x + self.radius * 2, draw_y + self.radius * 2),
                fill=CONFIG.BALL_FILL_COLOR, outline=CONFIG.BALL_OUTLINE_COLOR
            )
            
            # LCDに転送
            pixel_bytes = pil_to_rgb565_bytes(update_img)
            lcd.set_window(update_bbox[0], update_bbox[1], update_bbox[2] - 1, update_bbox[3] - 1)
            lcd.write_pixels(pixel_bytes)

        self.prev_bbox = curr_bbox

class FpsCounter:
    """FPSの計算と描画を管理するクラス"""
    def __init__(self, lcd, bg_img):
        try:
            self.font = ImageFont.truetype(CONFIG.FPS_FONT_PATH, CONFIG.FPS_FONT_SIZE)
            print(f"'{CONFIG.FPS_FONT_PATH}' フォントを読み込みました。")
        except IOError:
            print(f"警告: '{CONFIG.FPS_FONT_PATH}' が見つかりません。デフォルトフォントを使用します。")
            self.font = ImageFont.load_default()

        # 文字欠けを防ぐため、textbboxのオフセットを考慮した固定描画領域を計算
        padding = CONFIG.FPS_AREA_PADDING
        pos = (padding, padding)
        base_bbox = ImageDraw.Draw(bg_img).textbbox((0,0), "FPS: 999", font=self.font)
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

        if elapsed >= CONFIG.FPS_UPDATE_INTERVAL:
            fps = self.frame_count / elapsed
            fps_text = f"FPS: {fps:.0f}"
            
            # 描画処理
            text_img = self.bg_crop.copy()
            draw = ImageDraw.Draw(text_img)
            draw.text(self.draw_offset, fps_text, font=self.font, fill=CONFIG.FPS_TEXT_COLOR)
            
            pixel_bytes = pil_to_rgb565_bytes(text_img)
            lcd.set_window(self.bbox[0], self.bbox[1], self.bbox[2] - 1, self.bbox[3] - 1)
            lcd.write_pixels(pixel_bytes)
            
            # カウンタをリセット
            self.frame_count = 0
            self.last_update_time = current_time

# --- メイン処理 ---
def main():
    """メイン関数"""
    with ST7789V_Driver(speed_hz=CONFIG.SPI_SPEED_HZ) as lcd:
        print(f"フレームレートを約{CONFIG.TARGET_FPS}FPSに制限します... Ctrl+C で終了してください。")

        # 1. 背景画像を一度だけ生成し、画面全体に描画
        bg_img = Image.new("RGB", (lcd.width, lcd.height))
        draw = ImageDraw.Draw(bg_img)
        for y in range(lcd.height):
            color = (y % 256, (y*2) % 256, (y*3) % 256)
            draw.line((0, y, lcd.width, y), fill=color)
        lcd.display(bg_img)

        # 2. オブジェクトを初期化
        ball = Ball(50, 50, CONFIG.BALL_RADIUS, CONFIG.BALL_INITIAL_SPEED_X, CONFIG.BALL_INITIAL_SPEED_Y)
        fps_counter = FpsCounter(lcd, bg_img)
        
        # 3. メインループ
        last_frame_time = time.time()
        target_duration = 1.0 / CONFIG.TARGET_FPS

        while True:
            # --- 時間管理 ---
            frame_start_time = time.time()
            delta_t = frame_start_time - last_frame_time
            last_frame_time = frame_start_time

            # --- 更新と描画 ---
            ball.update_position(delta_t, lcd.width, lcd.height)
            ball.draw(lcd, bg_img)
            fps_counter.update_and_draw(lcd)

            # --- フレームレート制限 ---
            # 処理にかかった時間に応じて待機時間を計算し、CPU負荷を軽減する
            elapsed_time = time.time() - frame_start_time
            sleep_duration = target_duration - elapsed_time
            if sleep_duration > 0:
                time.sleep(sleep_duration)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n終了しました。")
