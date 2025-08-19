import pigpio
import time

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

class ST7789V_Driver:
    """
    ST7789Vディスプレイを制御する純粋なドライバークラス。(横型デフォルト版)

    pigpioライブラリに完全に依存し、GPIO制御とSPI通信の両方を担当。
    パフォーマンスと堅牢性を向上させるための改善が施されている。
    """
    # ST7789V コマンド定義
    CMD_NOP     = 0x00
    CMD_SWRESET = 0x01
    CMD_SLPOUT  = 0x11
    CMD_NORON   = 0x13
    CMD_INVON   = 0x21
    CMD_DISPOFF = 0x28
    CMD_DISPON  = 0x29
    CMD_CASET   = 0x2A
    CMD_RASET   = 0x2B
    CMD_RAMWR   = 0x2C
    CMD_MADCTL  = 0x36
    CMD_COLMOD  = 0x3A
    CMD_E0      = 0xE0 # Positive Voltage Gamma Control
    CMD_E1      = 0xE1 # Negative Voltage Gamma Control

    def __init__(self, channel=0, rst_pin=19, dc_pin=18, backlight_pin=20, 
                 speed_hz=80000000, width=240, height=320, rotation=90):
        """
        :param channel: SPIチャネル番号 (0=CE0, 1=CE1)
        :param rst_pin: リセット用GPIOピン番号
        :param dc_pin:  データ/コマンド選択用GPIOピン番号
        :param backlight_pin: バックライト制御用GPIOピン番号
        :param speed_hz: SPIクロック周波数
        :param width: ディスプレイの物理幅 (ピクセル)
        :param height: ディスプレイの物理高さ (ピクセル)
        :param rotation: 初期回転角度 (0, 90, 180, 270)

        デフォルトは ST7789V 標準の 240x320 パネルを横型(90°回転)で使用する。
        """
        self._native_width = width   # 物理パネルの幅 = 240
        self._native_height = height # 物理パネルの高さ = 320
        self.width = width
        self.height = height
        self._rotation = rotation

        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpio daemonが起動していません。'sudo pigpiod'で起動してください。")

        self.rst_pin = rst_pin
        self.dc_pin = dc_pin
        self.backlight_pin = backlight_pin

        self.pi.set_mode(self.rst_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.dc_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.backlight_pin, pigpio.OUTPUT)

        # pigpioのSPI機能で初期化
        # channel: CE0=0, CE1=1 を指定
        self.spi_handle = self.pi.spi_open(channel, speed_hz, 0)
        if self.spi_handle < 0:
            raise RuntimeError(f"SPIバスのオープンに失敗しました。エラーコード: {self.spi_handle}")

        self._buffer = None  # ダブルバッファリング用のバッファ
        self._init_display()
        self.set_rotation(self._rotation)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _init_buffer(self):
        """現在の画面サイズに基づいてバッファを初期化する"""
        self._buffer = bytearray(self.width * self.height * 2)

    def _write_command(self, command):
        self.pi.write(self.dc_pin, 0)
        self.pi.spi_write(self.spi_handle, [command])

    def _write_data(self, data):
        self.pi.write(self.dc_pin, 1)
        if isinstance(data, int):
            self.pi.spi_write(self.spi_handle, [data])
        else:
            self.pi.spi_write(self.spi_handle, data)

    def _init_display(self):
        self.pi.write(self.rst_pin, 1)
        time.sleep(0.01)
        self.pi.write(self.rst_pin, 0)
        time.sleep(0.01)
        self.pi.write(self.rst_pin, 1)
        time.sleep(0.150)

        self._write_command(self.CMD_SWRESET)
        time.sleep(0.150)
        self._write_command(self.CMD_SLPOUT)
        time.sleep(0.500)

        self._write_command(self.CMD_COLMOD)
        self._write_data(0x55)  # 16bit/pixel

        self._write_command(0xB2)
        self._write_data(bytes([0x0C, 0x0C, 0x00, 0x33, 0x33]))
        
        self._write_command(0xB7)
        self._write_data(0x35)
        
        self._write_command(0xBB)
        self._write_data(0x19)
        self._write_command(0xC0)
        self._write_data(0x2C)
        self._write_command(0xC2)
        self._write_data(bytes([0x01, 0xFF]))
        self._write_command(0xC3)
        self._write_data(0x11)
        self._write_command(0xC4)
        self._write_data(0x20)
        self._write_command(0xC6)
        self._write_data(0x0F)
        self._write_command(0xD0)
        self._write_data(bytes([0xA4, 0xA1]))

        # ガンマ補正
        self._write_command(self.CMD_E0)
        self._write_data(bytes([0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x32, 0x44, 0x42, 0x06, 0x0E, 0x12, 0x14, 0x17, 0x00]))
        self._write_command(self.CMD_E1)
        self._write_data(bytes([0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x31, 0x54, 0x47, 0x0E, 0x1C, 0x17, 0x1B, 0x1B, 0x00]))

        self._write_command(self.CMD_INVON)
        self._write_command(self.CMD_DISPON)
        time.sleep(0.1)
        self.pi.write(self.backlight_pin, 1)

    def set_rotation(self, rotation):
        """
        ディスプレイの回転を設定する。
        rotation が 90 または 270 の場合、幅と高さを入れ替える。
        """
        self._write_command(self.CMD_MADCTL)
        if rotation == 0:
            self._write_data(0x00)
            self.width, self.height = self._native_width, self._native_height  # 240x320
        elif rotation == 90:
            self._write_data(0x60)
            self.width, self.height = self._native_height, self._native_width  # 320x240
        elif rotation == 180:
            self._write_data(0xC0)
            self.width, self.height = self._native_width, self._native_height  # 240x320
        elif rotation == 270:
            self._write_data(0xA0)
            self.width, self.height = self._native_height, self._native_width  # 320x240
        else:
            raise ValueError("Rotation must be 0, 90, 180, or 270.")
        self._rotation = rotation
        self._init_buffer()
            
    def set_window(self, x0, y0, x1, y1):
        self._write_command(self.CMD_CASET)
        self._write_data(bytearray([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._write_command(self.CMD_RASET)
        self._write_data(bytearray([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._write_command(self.CMD_RAMWR)

    def write_pixels(self, pixel_bytes):
        self.pi.write(self.dc_pin, 1)
        chunk_size = 4096 
        for i in range(0, len(pixel_bytes), chunk_size):
            chunk = pixel_bytes[i:i + chunk_size]
            self.pi.spi_write(self.spi_handle, chunk)

    def display(self, image):
        """
        PIL Imageオブジェクトを画面に表示する。
        内部バッファに変換してから一括でSPI転送する（ダブルバッファリング）。
        numpyが利用可能な場合は、高速な変換を行う。
        """
        if image.mode != "RGB":
            image = image.convert("RGB")
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))

        if _NUMPY_AVAILABLE:
            # numpy を使った高速な変換
            np_img = np.array(image, dtype=np.uint8)
            r = (np_img[:, :, 0] >> 3).astype(np.uint16)
            g = (np_img[:, :, 1] >> 2).astype(np.uint16)
            b = (np_img[:, :, 2] >> 3).astype(np.uint16)
            rgb565 = (r << 11) | (g << 5) | b
            self._buffer = rgb565.byteswap().tobytes()
        else:
            # PIL のみを使った変換 (低速)
            pixel_data = []
            w, h = image.size
            for y in range(h):
                for x in range(w):
                    r, g, b = image.getpixel((x, y))
                    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    pixel_data.append(rgb565 >> 8)
                    pixel_data.append(rgb565 & 0xFF)
            self._buffer = bytearray(pixel_data)

        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.write_pixels(self._buffer)

    def close(self):
        try:
            self.pi.write(self.backlight_pin, 0)
            if hasattr(self, 'spi_handle') and self.spi_handle >= 0:
                self.pi.spi_close(self.spi_handle)
        finally:
            if self.pi.connected:
                self.pi.stop()

# --- 使用例 ---
if __name__ == '__main__':
    from PIL import Image
    print("ST7789V ドライバテスト開始")
    try:
        # SPI速度を安定していた40MHzに戻してテスト
        with ST7789V_Driver(speed_hz=40000000) as lcd:
            print("初期化成功。新しいdisplay()メソッドで画面を青色で塗りつぶします...")
            
            # 青一色のPIL Imageオブジェクトを作成
            img = Image.new("RGB", (lcd.width, lcd.height), "blue")
            
            # 新しいdisplayメソッドで描画
            lcd.display(img)
            
            time.sleep(3)
            print("テスト完了")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

