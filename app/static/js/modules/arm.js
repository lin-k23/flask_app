// app/static/js/modules/arm.js

export function initArm() {
    // 获取UI元素
    const receivedLogEl = document.getElementById('arm-log-received');
    const visionLogEl = document.getElementById('vision-send-log');

    // 获取所有开关
    const blobSwitch = document.getElementById('send-blob-switch');
    const tagSwitch = document.getElementById('send-tag-switch');
    const yoloSwitch = document.getElementById('send-yolo-switch'); // <--- 确保获取YOLO开关

    // 定时器ID变量
    let blobIntervalId = null;
    let tagIntervalId = null;
    let yoloIntervalId = null; // <--- 为YOLO添加定时器ID
    const SEND_INTERVAL = 500; // 每500毫秒发送一次

    // 通用日志函数
    function logTo(element, message) {
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
        element.insertBefore(p, element.firstChild); // 将新日志插入到最前面
    }

    // 1. 定时获取接收日志 (不变)
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
                }
            })
            .catch(error => console.error('获取机械臂状态失败:', error));
    }
    setInterval(fetchArmStatus, 2000);

    // 2. 发送视觉数据的通用函数 (不变)
    function sendVisionData(type) {
        const typeMap = {
            'color_block': '色块',
            'apriltag': 'AprilTag',
            'yolo_target': 'YOLO目标'
        };
        logTo(visionLogEl, `请求发送 ${typeMap[type]} 数据...`);

        fetch('/api/send_vision_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' || data.message.includes("警告")) {
                    logTo(visionLogEl, `后端响应: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('发送视觉数据失败:', error);
                logTo(visionLogEl, `错误: ${error}`);
            });
    }

    // 3. 为所有开关绑定事件
    blobSwitch.addEventListener('change', function () {
        if (this.checked) {
            logTo(visionLogEl, '已开启 [色块] 持续发送...');
            if (blobIntervalId === null) {
                blobIntervalId = setInterval(() => sendVisionData('color_block'), SEND_INTERVAL);
            }
        } else {
            logTo(visionLogEl, '已停止 [色块] 持续发送。');
            clearInterval(blobIntervalId);
            blobIntervalId = null;
        }
    });

    tagSwitch.addEventListener('change', function () {
        if (this.checked) {
            logTo(visionLogEl, '已开启 [AprilTag] 持续发送...');
            if (tagIntervalId === null) {
                tagIntervalId = setInterval(() => sendVisionData('apriltag'), SEND_INTERVAL);
            }
        } else {
            logTo(visionLogEl, '已停止 [AprilTag] 持续发送。');
            clearInterval(tagIntervalId);
            tagIntervalId = null;
        }
    });

    // --- [核心修正] 为YOLO开关添加事件监听 ---
    yoloSwitch.addEventListener('change', function () {
        if (this.checked) {
            logTo(visionLogEl, '已开启 [YOLO目标] 持续发送...');
            if (yoloIntervalId === null) {
                yoloIntervalId = setInterval(() => sendVisionData('yolo_target'), SEND_INTERVAL);
            }
        } else {
            logTo(visionLogEl, '已停止 [YOLO目标] 持续发送。');
            clearInterval(yoloIntervalId);
            yoloIntervalId = null;
        }
    });
}