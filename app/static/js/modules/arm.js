// app/static/js/modules/arm.js (解决冲突的最终版本)

export function initArm() {
    const receivedLogEl = document.getElementById('arm-log-received');
    const visionLogEl = document.getElementById('vision-send-log');

    // 我们将所有开关视为一个整体，同步它们的状态
    const allSwitches = [
        document.getElementById('send-blob-switch'),
        document.getElementById('send-tag-switch'),
        document.getElementById('send-yolo-switch')
    ].filter(sw => sw !== null); // 过滤掉不存在的开关

    // --- 日志获取逻辑 ---
    function fetchArmStatus() {
        fetch('/api/arm_status')
            .then(response => response.json())
            .then(data => {
                if (data.log && receivedLogEl) {
                    receivedLogEl.innerHTML = '';
                    data.log.slice().reverse().forEach(msg => {
                        const p = document.createElement('p');
                        p.textContent = `< ${msg}`;
                        receivedLogEl.appendChild(p);
                    });
                }
            })
            .catch(error => console.error('获取机械臂接收日志失败:', error));
    }

    function fetchArmSentLog() {
        fetch('/api/arm_sent_log')
            .then(response => response.json())
            .then(data => {
                if (data.log && visionLogEl) {
                    visionLogEl.innerHTML = '';
                    data.log.slice().reverse().forEach(msg => {
                        const p = document.createElement('p');
                        p.textContent = `> ${msg}`;
                        visionLogEl.appendChild(p);
                    });
                }
            })
            .catch(error => console.error('获取机械臂发送日志失败:', error));
    }

    // --- 状态同步逻辑 ---
    let isUpdatingSwitch = false; // 标志位，防止事件循环
    function fetchVisionStreamStatus() {
        fetch('/api/arm_vision_stream_status')
            .then(res => res.json())
            .then(data => {
                isUpdatingSwitch = true;
                allSwitches.forEach(sw => {
                    if (sw.checked !== data.is_active) {
                        sw.checked = data.is_active;
                    }
                });
                setTimeout(() => { isUpdatingSwitch = false; }, 100);
            })
            .catch(error => console.error('获取视觉流状态失败:', error));
    }

    // 设置所有定时器
    setInterval(fetchArmStatus, 1000);
    setInterval(fetchArmSentLog, 1000);
    setInterval(fetchVisionStreamStatus, 1000);

    // --- 开关事件监听逻辑 ---
    allSwitches.forEach(sw => {
        sw.addEventListener('change', function () {
            if (isUpdatingSwitch) return;

            const isEnabled = this.checked;
            console.log(`User toggled vision stream to: ${isEnabled}`);

            // 向后端发送状态变更请求
            fetch('/api/toggle_arm_vision_stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: isEnabled }),
            })
                .then(res => res.json())
                .then(data => {
                    console.log(data.message);
                    // 立即触发一次状态更新，确保UI快速同步
                    fetchVisionStreamStatus();
                });
        });
    });
}