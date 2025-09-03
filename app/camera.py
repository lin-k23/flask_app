# 导入新版MaixPy的摄像头模块
from maix import camera

# 定义一个常量来存储临时文件路径，使用/tmp通常会写入RAM
TEMP_FRAME_PATH = "/tmp/flask_frame.jpg"

class Camera:
    def __init__(self, width=320, height=240):
        """
        使用 maix.camera API 初始化摄像头
        """
        try:
            # 实例化摄像头对象，可以指定分辨率
            self.cam = camera.Camera(width, height)
            print(f"MaixPy Camera Initialized Successfully ({width}x{height})")
        except Exception as e:
            raise RuntimeError(f"Could not start MaixPy camera: {e}")

    def __del__(self):
        """
        在对象销_modules毁时，确保摄像头资源被关闭
        """
        if hasattr(self, 'cam'):
            self.cam.close()
        print("MaixPy Camera closed.")

    def get_frame(self):
        """
        获取一帧图像，将其保存到临时文件，然后读取并返回JPEG字节流
        """
        # 从摄像头获取一帧图像
        img = self.cam.read()
        if not img:
            return None
        
        # 根据之前的错误提示，save()方法需要一个字符串路径作为参数。
        # 我们将图像保存到/tmp下的一个临时文件。
        err = img.save(TEMP_FRAME_PATH, quality=90)
        if err != 0:
            print(f"Error saving frame: {err}")
            return None

        # 从刚刚保存的文件中读取所有字节
        with open(TEMP_FRAME_PATH, "rb") as f:
            frame_bytes = f.read()
            
        return frame_bytes