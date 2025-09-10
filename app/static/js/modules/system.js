// app/static/js/modules/system.js

export function initSystemControls() {
    const btnRefresh = document.getElementById('btn-refresh-page');
    const btnRestart = document.getElementById('btn-soft-restart');
    const btnShutdown = document.getElementById('btn-shutdown');
    // --- [核心修改] 更新按钮ID ---
    const btnSimulate1 = document.getElementById('btn-simulate-task1');
    const btnSimulate2 = document.getElementById('btn-simulate-task2');

    btnRefresh.addEventListener('click', () => {
        location.reload();
    });

    btnRestart.addEventListener('click', () => {
        if (confirm('您确定要重启所有后台服务吗？\n这将重置所有硬件连接。')) {
            fetch('/api/soft_restart', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    location.reload();
                })
                .catch(err => alert('重启失败:', err));
        }
    });

    btnShutdown.addEventListener('click', () => {
        if (confirm('警告：此操作将完全关闭服务器程序！\n您需要手动重新启动它。\n\n您确定要继续吗？')) {
            fetch('/api/shutdown', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    document.body.innerHTML = `<h1>${data.message}</h1><p>您可以安全地关闭此浏览器标签页了。</p>`;
                })
                .catch(err => {
                    document.body.innerHTML = `<h1>服务器正在关闭...</h1><p>连接已断开，您可以安全地关闭此浏览器标签页了。</p>`;
                });
        }
    });

    // --- [核心修改] 分别为两个按钮添加事件 ---
    btnSimulate1.addEventListener('click', () => {
        console.log("Attempting to start task 1 simulation...");
        fetch('/api/simulate_task1_start', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status !== 'success') {
                    alert(`模拟启动失败: ${data.message}`);
                } else {
                    alert(`模拟任务1已启动: ${data.message}`);
                }
            })
            .catch(err => alert('启动模拟1失败:', err));
    });

    btnSimulate2.addEventListener('click', () => {
        console.log("Attempting to start task 2 simulation...");
        fetch('/api/simulate_task2_start', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status !== 'success') {
                    alert(`模拟启动失败: ${data.message}`);
                } else {
                    alert(`模拟任务2已启动: ${data.message}`);
                }
            })
            .catch(err => alert('启动模拟2失败:', err));
    });
}