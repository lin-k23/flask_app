// app/static/js/modules/arm.js

export function initArm() {
    const receivedLogEl = document.getElementById('arm-log-received');
    const visionLogEl = document.getElementById('vision-send-log');

    const allSwitches = [
        document.getElementById('send-blob-switch'),
        document.getElementById('send-tag-switch'),
    ].filter(sw => sw !== null);

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

    let isUpdatingSwitch = false;
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

    setInterval(fetchArmStatus, 1000);
    setInterval(fetchArmSentLog, 1000);
    setInterval(fetchVisionStreamStatus, 1000);

    allSwitches.forEach(sw => {
        sw.addEventListener('change', function () {
            if (isUpdatingSwitch) return;

            const isEnabled = this.checked;

            fetch('/api/toggle_arm_vision_stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: isEnabled }),
            })
                .then(res => res.json())
                .then(data => {
                    fetchVisionStreamStatus();
                });
        });
    });
}