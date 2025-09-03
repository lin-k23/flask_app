// --- Part 4: Arm Communication Logic ---

export function initArm() {
    // 获取所有UI元素
    const receivedLogEl = document.getElementById('arm-log-received');
    const visionLogEl = document.getElementById('vision-send-log');
    const customCommandInput = document.getElementById('arm-command');
    const sendCustomBtn = document.getElementById('send-arm-command');
    const sendBlobBtn = document.getElementById('send-blob-data');
    const sendTagBtn = document.getElementById('send-tag-data');

    // 通用日志函数
    function logTo(element, message) {
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
        element.appendChild(p);
        element.scrollTop = element.scrollHeight; // 自动滚动到底部
    }

    // 1. 定时获取并显示接收到的日志
    function fetchArmStatus() {
        fetch('/api/arm_status')
            .then(response => response.json())
            .then(data => {
                if (data.log && data.log.length > 0) {
                    receivedLogEl.innerHTML = ''; // 清空旧日志
                    data.log.forEach(msg => {
                        const p = document.createElement('p');
                        p.textContent = `< ${msg}`; // 使用 '<' 表示接收
                        receivedLogEl.appendChild(p);
                    });
                    receivedLogEl.scrollTop = receivedLogEl.scrollHeight;
                } else {
                    // 如果没有日志，可以显示一个占位符
                    receivedLogEl.innerHTML = '<p>> 暂无新消息</p>';
                }
            })
            .catch(error => console.error('获取机械臂状态失败:', error));
    }
    setInterval(fetchArmStatus, 2000); // 每2秒刷新一次

    // 2. 发送视觉数据
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
                logTo(visionLogEl, `后端响应: ${data.message}`);
            })
            .catch(error => {
                console.error('发送视觉数据失败:', error);
                logTo(visionLogEl, `错误: ${error}`);
            });
    }

    sendBlobBtn.addEventListener('click', () => sendVisionData('color_block'));
    sendTagBtn.addEventListener('click', () => sendVisionData('apriltag'));

    // 3. 发送自定义指令
    function sendCustomCommand() {
        const command = customCommandInput.value;
        if (!command) return;

        logTo(visionLogEl, `发送自定义指令: ${command}`); // 也在发送日志里记录

        fetch('/api/send_arm_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command }),
        })
            .then(response => response.json())
            .then(data => {
                logTo(visionLogEl, `后端响应: ${data.message}`);
            })
            .catch(error => {
                console.error('发送自定义指令失败:', error);
                logTo(visionLogEl, `错误: ${error}`);
            });
        customCommandInput.value = '';
    }

    sendCustomBtn.addEventListener('click', sendCustomCommand);
    customCommandInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendCustomCommand();
        }
    });
}

