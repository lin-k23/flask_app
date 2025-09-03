# TODO: 在这里实现与机械臂通信和控制的所有逻辑


def send_command(command):
    print(f"向机械臂发送指令: {command}")
    # serial.write(command.encode())


def get_status():
    print("获取机械臂状态")
    # return serial.read()


# ... 其他控制函数 ...
