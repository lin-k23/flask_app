// app/static/js/modules/car.js

export function initCarControls() {
    // --- 获取UI元素 ---
    const controlButtons = document.querySelectorAll('.car-btn');
    const carLogReceivedEl = document.getElementById('car-log-received');
    const carSpeedInput = document.getElementById('car-speed');
    const carLogSentEl = document.getElementById('car-log-sent');

    // 1. 为手动控制按钮添加点击事件
    controlButtons.forEach(button => {
        button.addEventListener('click', () => {
            const action = button.dataset.command;
            const speed = carSpeedInput.value;
            let command = (action === 'stop') ? `{${action}}` : `{${action}:${speed}}`;
            sendCarCommand(command);
        });
    });

    // --- 核心发送逻辑 ---
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
        // 在日志开头插入新消息，而不是末尾追加
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
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