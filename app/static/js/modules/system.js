// app/static/js/modules/system.js

export function initSystemControls() {
    const btnRefresh = document.getElementById('btn-refresh-page');
    const btnRestart = document.getElementById('btn-soft-restart');
    const btnShutdown = document.getElementById('btn-shutdown');

    // 1. 刷新页面
    btnRefresh.addEventListener('click', () => {
        location.reload();
    });

    // 2. 重启服务
    btnRestart.addEventListener('click', () => {
        if (confirm('您确定要重启所有后台服务吗？\n这将重置所有硬件连接。')) {
            fetch('/api/soft_restart', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    location.reload(); // 重启后刷新页面以确保所有状态更新
                })
                .catch(err => alert('重启失败:', err));
        }
    });

    // 3. 关闭程序
    btnShutdown.addEventListener('click', () => {
        if (confirm('警告：此操作将完全关闭服务器程序！\n您需要手动重新启动它。\n\n您确定要继续吗？')) {
            fetch('/api/shutdown', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    // 显示消息，然后页面可能会因为服务器关闭而无响应
                    document.body.innerHTML = `<h1>${data.message}</h1><p>您可以安全地关闭此浏览器标签页了。</p>`;
                })
                .catch(err => {
                    // 如果fetch失败，很可能是因为服务器已经关闭了
                    document.body.innerHTML = `<h1>服务器正在关闭...</h1><p>连接已断开，您可以安全地关闭此浏览器标签页了。</p>`;
                });
        }
    });
}