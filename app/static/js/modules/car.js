// 文件: app/static/js/modules/car.js (最终修正版)

export function initCarControls() {
    // --- 获取所有需要交互的UI元素 ---
    const controlButtons = document.querySelectorAll('.car-btn');
    const modeButtons = document.querySelectorAll('.car-mode-btn');
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

    // 2. 为模式切换按钮添加点击事件
    modeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const command = button.dataset.command;
            sendCarCommand(command);
        });
    });

    // 3. 核心发送逻辑 (现在只负责发送)
    function sendCarCommand(command) {
        // [核心修改] 不再调用 logToCarSent, 后端会自动记录
        fetch('/api/send_car_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command }),
        })
            .then(response => response.json())
            .then(data => console.log('Backend response:', data.message))
            .catch(error => console.error('发送小车指令失败:', error));
    }

    // 4. 日志与状态更新
    function fetchCarStatus() {
        fetch('/api/car_status')
            .then(response => response.json())
            .then(data => {
                if (data.log) { // 检查log是否存在
                    carLogReceivedEl.innerHTML = ''; // 先清空
                    data.log.slice().reverse().forEach(msg => { // 反转数组，让最新的在最上面
                        const p = document.createElement('p');
                        p.textContent = `< ${msg}`;
                        carLogReceivedEl.appendChild(p);
                    });
                }
            })
            .catch(error => console.error('获取小车接收日志失败:', error));
    }

    // --- [新增] 新的函数，用于从后端获取发送日志 ---
    function fetchCarSentLog() {
        fetch('/api/car_sent_log')
            .then(response => response.json())
            .then(data => {
                if (data.log) { // 检查log是否存在
                    carLogSentEl.innerHTML = ''; // 先清空
                    data.log.slice().reverse().forEach(msg => { // 反转数组，让最新的在最上面
                        const p = document.createElement('p');
                        p.textContent = `> ${msg}`;
                        carLogSentEl.appendChild(p);
                    });
                }
            })
            .catch(error => console.error('获取小车发送日志失败:', error));
    }

    // --- [修改] 设置定时器，同时获取接收和发送的日志 ---
    setInterval(fetchCarStatus, 1000); // 周期可以调整，比如1秒
    setInterval(fetchCarSentLog, 1000);
}