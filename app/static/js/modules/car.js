// --- Part 3: Trajectory Logic ---

export function initTrajectory() {
    const canvas = document.getElementById('trajectory-canvas');
    const ctx = canvas.getContext('2d');
    let x = canvas.width / 2;
    let y = canvas.height / 2;

    function drawTrajectory() {
        // 绘制轨迹的占位逻辑
        ctx.fillStyle = '#3f51b5';
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fill();

        // 模拟运动
        x += (Math.random() - 0.5) * 5;
        y += (Math.random() - 0.5) * 5;

        // 边界检查
        if (x < 0) x = 0; if (x > canvas.width) x = canvas.width;
        if (y < 0) y = 0; if (y > canvas.height) y = canvas.height;
    }

    // 每500毫秒更新一次轨迹
    setInterval(drawTrajectory, 500);
}
