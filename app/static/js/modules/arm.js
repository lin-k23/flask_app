// --- Part 4: Arm Communication Logic ---

export function initArm() {
    // 获取所有UI元素
    const receivedLogEl = document.getElementById('arm-log-received');
    const visionLogEl = document.getElementById('vision-send-log');
    // const customCommandInput = document.getElementById('arm-command');
    // const sendCustomBtn = document.getElementById('send-arm-command');

    // --- [新功能] 获取开关元素 ---
    const blobSwitch = document.getElementById('send-blob-switch');
    const tagSwitch = document.getElementById('send-tag-switch');

    // --- [新功能] 定时器ID变量 ---
    let blobIntervalId = null;
    let tagIntervalId = null;
    const SEND_INTERVAL = 500; // 每500毫秒发送一次

    // 通用日志函数
    function logTo(element, message) {
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
        element.appendChild(p);
        element.scrollTop = element.scrollHeight; // 自动滚动到底部
    }

    // 1. 定时获取并显示接收到的日志 (不变)
    function fetchArmStatus() {
        fetch('/api/arm_status')
            .then(response => response.json())
            .then(data => {
                if (data.log && data.log.length > 0) {
                    receivedLogEl.innerHTML = '';
                    data.log.forEach(msg => {
                        const p = document.createElement('p');
                        p.textContent = `< ${msg}`;
                        receivedLogEl.appendChild(p);
                    });
                    receivedLogEl.scrollTop = receivedLogEl.scrollHeight;
                } else {
                    receivedLogEl.innerHTML = '<p>> 暂无新消息</p>';
                }
            })
            .catch(error => console.error('获取机械臂状态失败:', error));
    }
    setInterval(fetchArmStatus, 2000);

    // 2. 发送视觉数据 (不变)
    function sendVisionData(type) {
        const logMessage = `请求发送 ${type === 'color_block' ? '色块' : 'AprilTag'} 数据...`;
        logTo(visionLogEl, logMessage);

        fetch('/api/send_vision_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type }),
        })
            .then(response => response.json())
            .then(data => {
                // 只在后端成功发送时才记录日志，避免刷屏
                if (data.status === 'success') {
                    logTo(visionLogEl, `后端响应: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('发送视觉数据失败:', error);
                logTo(visionLogEl, `错误: ${error}`);
            });
    }

    // --- [新功能] 监听开关状态变化 ---
    blobSwitch.addEventListener('change', function () {
        if (this.checked) {
            // 如果开关打开，启动定时器
            logTo(visionLogEl, '已开启 [色块] 持续发送...');
            if (blobIntervalId === null) {
                blobIntervalId = setInterval(() => sendVisionData('color_block'), SEND_INTERVAL);
            }
        } else {
            // 如果开关关闭，清除定时器
            logTo(visionLogEl, '已停止 [色块] 持续发送。');
            clearInterval(blobIntervalId);
            blobIntervalId = null;
        }
    });

    tagSwitch.addEventListener('change', function () {
        if (this.checked) {
            // 如果开关打开，启动定时器
            logTo(visionLogEl, '已开启 [AprilTag] 持续发送...');
            if (tagIntervalId === null) {
                tagIntervalId = setInterval(() => sendVisionData('apriltag'), SEND_INTERVAL);
            }
        } else {
            // 如果开关关闭，清除定时器
            logTo(visionLogEl, '已停止 [AprilTag] 持续发送。');
            clearInterval(tagIntervalId);
            tagIntervalId = null;
        }
    });


    // 3. 发送自定义指令 (不变)
    // function sendCustomCommand() {
    //     const command = customCommandInput.value;
    //     if (!command) return;
    //     logTo(visionLogEl, `发送自定义指令: ${command}`);
    //     fetch('/api/send_arm_command', {
    //         method: 'POST',
    //         headers: { 'Content-Type': 'application/json' },
    //         body: JSON.stringify({ command: command }),
    //     })
    //         .then(response => response.json())
    //         .then(data => {
    //             logTo(visionLogEl, `后端响应: ${data.message}`);
    //         })
    //         .catch(error => {
    //             console.error('发送自定义指令失败:', error);
    //             logTo(visionLogEl, `错误: ${error}`);
    //         });
    //     customCommandInput.value = '';
    // }
    // sendCustomBtn.addEventListener('click', sendCustomCommand);
    // customCommandInput.addEventListener('keypress', function (e) {
    //     if (e.key === 'Enter') { sendCustomCommand(); }
    // });
}