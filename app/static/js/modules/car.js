// 文件: app/static/js/modules/car.js (最终修正版)

export function initCarControls() {
    // --- 获取所有需要交互的UI元素 ---
    const controlButtons = document.querySelectorAll('.car-btn');
    const modeButtons = document.querySelectorAll('.car-mode-btn'); // <--- 确保选中了模式按钮
    const carLogReceivedEl = document.getElementById('car-log-received');
    const carSpeedInput = document.getElementById('car-speed');
    const carLogSentEl = document.getElementById('car-log-sent');

    // 1. 为手动控制的方向按钮添加点击事件
    controlButtons.forEach(button => {
        button.addEventListener('click', () => {
            const action = button.dataset.command;
            const speed = carSpeedInput.value;
            let command = (action === 'stop') ? `{${action}}` : `{${action}:${speed}}`;
            sendCarCommand(command);
        });
    });

    // 2. [核心修正] 为模式切换按钮添加点击事件
    modeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const command = button.dataset.command; // 例如: "{auto_track_start}"
            sendCarCommand(command);
        });
    });

    // --- 核心发送逻辑 (被所有按钮调用) ---
    function sendCarCommand(command) {
        logToCarSent(command);
        fetch('/api/send_car_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command }),
        })
            .then(response => response.json())
            .then(data => console.log('Backend response:', data.message))
            .catch(error => console.error('发送小车指令失败:', error));
    }

    // --- 日志与状态更新 ---
    function logToCarSent(message) {
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
        // 将新日志插入到最前面，而不是追加到末尾
        carLogSentEl.insertBefore(p, carLogSentEl.firstChild);
    }

    function fetchCarStatus() {
        fetch('/api/car_status')
            .then(response => response.json())
            .then(data => {
                if (data.log && data.log.length > 0) {
                    carLogReceivedEl.innerHTML = '';
                    data.log.forEach(msg => {
                        const p = document.createElement('p');
                        p.textContent = `< ${msg}`;
                        carLogReceivedEl.appendChild(p);
                    });
                    carLogReceivedEl.scrollTop = carLogReceivedEl.scrollHeight;
                }
            })
            .catch(error => console.error('获取小车状态失败:', error));
    }
    setInterval(fetchCarStatus, 2000);
}