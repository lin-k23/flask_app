# # 导入需要的库
from maix import camera, display, image, app

# --- 1. 视觉配置 ---

# ==========================================================
# == 在这里修改你要测试的LAB颜色阈值 ==
# 格式: [[L_min, L_max, A_min, A_max, B_min, B_max]]
# color_thresholds = [[0, 80, 40, 60, 40, 80]]  # 橙色
# color_thresholds = [[28,68,12, 52, -80, -40]]    # 紫色
color_thresholds = [[0,80,-15, 15, 50, 80]]    # 黄色
# color_thresholds = [[0,80,-10, 10, -55, -30]]    # 蓝色
# ==========================================================

# 摄像头分辨率
CAM_WIDTH = 320
CAM_HEIGHT = 240

# 色块识别的最小面积阈值（像素），用于过滤掉微小的噪点
# 如果目标物体很小或很远，可以适当调低这个值
PIXELS_THRESHOLD = 150
AREA_THRESHOLD = 150


# --- 2. 硬件初始化 ---
try:
    cam = camera.Camera(CAM_WIDTH, CAM_HEIGHT)
    disp = display.Display()
    print("程序启动成功，请将目标色块对准摄像头。")
    print("观察屏幕上绿色框是否能稳定地框选目标。")
    print(f"当前测试阈值: {color_thresholds}")

except Exception as e:
    print(f"硬件初始化失败: {e}")
    app.set_exit_flag(True)


# --- 3. 主程序循环 ---
while not app.need_exit():
    # 读取一帧图像
    img = cam.read()

    # 使用设定的阈值寻找色块
    # merge=True 会将找到的邻近小色块合并成一个大色块
    blobs = img.find_blobs(color_thresholds, pixels_threshold=PIXELS_THRESHOLD, area_threshold=AREA_THRESHOLD, merge=True)

    # 如果找到了色块
    if blobs:
        # 遍历所有找到的色块
        for b in blobs:
            # --- 使用 draw_line 手动绘制矩形框 ---
            # b.rect() 返回一个元组 (x, y, w, h)
            rect_corners = b.rect()
            p1 = (rect_corners[0], rect_corners[1])
            p2 = (rect_corners[0] + rect_corners[2], rect_corners[1])
            p3 = (rect_corners[0] + rect_corners[2], rect_corners[1] + rect_corners[3])
            p4 = (rect_corners[0], rect_corners[1] + rect_corners[3])
            
            # 绘制四条边
            img.draw_line(p1[0], p1[1], p2[0], p2[1], image.COLOR_GREEN, 2)
            img.draw_line(p2[0], p2[1], p3[0], p3[1], image.COLOR_GREEN, 2)
            img.draw_line(p3[0], p3[1], p4[0], p4[1], image.COLOR_GREEN, 2)
            img.draw_line(p4[0], p4[1], p1[0], p1[1], image.COLOR_GREEN, 2)
            # ----------------------------------------
            
            # 在框的上方显示色块的面积信息
            img.draw_string(b.x(), b.y() - 15, f"Area:{b.area()}", color=image.COLOR_GREEN, scale=1.5)

    # 将处理后的图像显示在屏幕上
    disp.show(img)