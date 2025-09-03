// app/static/js/modules/car.js

export function initCarControls() {
    // --- 获取所有UI元素 ---
    const controlButtons = document.querySelectorAll('.car-btn');
    const carLogReceivedEl = document.getElementById('car-log-received');
    const carSpeedInput = document.getElementById('car-speed');
    const carLogSentEl = document.getElementById('car-log-sent');

    // --- [新功能] 获取新增的UI元素 ---
    const modeButtons = document.querySelectorAll('.car-mode-btn');
    const customCommandInput = document.getElementById('car-command');
    const sendCustomBtn = document.getElementById('send-car-command');

    // 1. 为手动控制按钮添加点击事件
    controlButtons.forEach(button => {
        button.addEventListener('click', () => {
            const action = button.dataset.command;
            const speed = carSpeedInput.value;
            let command = (action === 'stop') ? `{${action}}` : `{${action}:${speed}}`;
            sendCarCommand(command);
        });
    });

    // --- [新功能] 2. 为模式切换按钮添加点击事件 ---
    modeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const command = button.dataset.command;
            sendCarCommand(command);
        });
    });

    // --- [新功能] 3. 实现发送自定义指令的功能 ---
    function sendCustomCarCommand() {
        const command = customCommandInput.value;
        if (!command) return; // 如果输入为空则不发送
        sendCarCommand(command);
        customCommandInput.value = ''; // 发送后清空输入框
    }
    sendCustomBtn.addEventListener('click', sendCustomCarCommand);
    customCommandInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendCustomCarCommand();
        }
    });

    // --- 核心发送逻辑 (现在被多处调用) ---
    function sendCarCommand(command) {
        logToCarSent(command); // 记录到发送日志

        fetch('/api/send_car_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command }),
        })
            .then(response => response.json())
            .then(data => {
                console.log('Backend response:', data.message);
            })
            .catch(error => console.error('发送小车指令失败:', error));
    }

    // --- 日志与状态更新 (保持不变) ---
    function logToCarSent(message) {
        const p = document.createElement('p');
        p.textContent = `> ${message}`;
        carLogSentEl.appendChild(p);
        carLogSentEl.scrollTop = carLogSentEl.scrollHeight;
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
                } else {
                    carLogReceivedEl.innerHTML = '<p>> 暂无新消息</p>';
                }
            })
            .catch(error => console.error('获取小车状态失败:', error));
    }
    setInterval(fetchCarStatus, 2000);
}