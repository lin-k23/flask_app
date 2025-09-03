// --- Part 4: Arm Communication Logic ---

export function initArm() {
    const armLog = document.getElementById('arm-log');
    const armCommandInput = document.getElementById('arm-command');
    const sendArmCommandBtn = document.getElementById('send-arm-command');

    function logToArm(message, sender = 'SYS') {
        const p = document.createElement('p');
        p.textContent = `[${sender}] > ${message}`;
        armLog.appendChild(p);
        armLog.scrollTop = armLog.scrollHeight;
    }

    function sendArmCommand() {
        const command = armCommandInput.value;
        if (!command) return;
        logToArm(command, 'YOU');

        fetch('/api/send_arm_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command }),
        })
            .then(response => response.json())
            .then(data => { logToArm(data.message, 'ARM'); })
            .catch(error => {
                console.error('发送指令失败:', error);
                logToArm('通讯错误!', 'ERR');
            });
        armCommandInput.value = '';
    }

    sendArmCommandBtn.addEventListener('click', sendArmCommand);
    armCommandInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendArmCommand();
        }
    });

    logToArm('通讯系统已就绪。');
}
