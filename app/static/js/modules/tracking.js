// app/static/js/modules/tracking.js (已修正)

export function initTracking() {
    const cameraFeed = document.getElementById('camera-feed');
    // 修正：使用新的 wrapper 作为交互和定位的基准
    const cameraWrapper = document.getElementById('camera-wrapper');

    if (!cameraWrapper || !cameraFeed) {
        console.error("错误：未找到 camera-feed 或 camera-wrapper 元素！");
        return;
    }

    // --- 1. 创建用于框选的UI元素 ---
    const selectionBox = document.createElement('div');
    selectionBox.style.position = 'absolute';
    selectionBox.style.border = '2px dashed #ff3333';
    selectionBox.style.backgroundColor = 'rgba(255, 0, 0, 0.15)'; // 增加半透明背景
    selectionBox.style.display = 'none';
    selectionBox.style.pointerEvents = 'none'; // 确保鼠标事件能穿透
    cameraWrapper.appendChild(selectionBox); // 附加到 wrapper

    // --- 2. 创建控制按钮 (逻辑不变) ---
    const btnStart = document.createElement('button');
    btnStart.textContent = '选择目标并追踪';
    btnStart.className = 'system-btn btn-blue';

    const btnStop = document.createElement('button');
    btnStop.textContent = '停止追踪';
    btnStop.className = 'system-btn btn-red';
    btnStop.style.display = 'none';

    const systemControls = document.querySelector('.panel-system-controls .system-buttons');
    if (systemControls) {
        // 移除旧按钮（如果有）
        const oldStart = document.getElementById('btn-start-tracking');
        const oldStop = document.getElementById('btn-stop-tracking');
        if (oldStart) oldStart.remove();
        if (oldStop) oldStop.remove();

        // 添加新按钮
        btnStart.id = 'btn-start-tracking';
        btnStop.id = 'btn-stop-tracking';
        systemControls.appendChild(btnStart);
        systemControls.appendChild(btnStop);
    }

    let isSelecting = false;
    let isTracking = false;
    let startX, startY;

    // --- 3. 核心修正：重构事件绑定和坐标计算 ---

    btnStart.addEventListener('click', () => {
        alert('请在摄像头画面上按住鼠标左键并拖动来选择目标。');
        cameraWrapper.style.cursor = 'crosshair';
    });

    btnStop.addEventListener('click', stopTracking);

    // 绑定到 wrapper，而不是 img
    cameraWrapper.addEventListener('mousedown', (e) => {
        if (isTracking || e.button !== 0) return; // 只响应左键
        e.preventDefault(); // 阻止浏览器默认的图片拖拽行为

        isSelecting = true;
        const rect = cameraWrapper.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;

        selectionBox.style.left = startX + 'px';
        selectionBox.style.top = startY + 'px';
        selectionBox.style.width = '0px';
        selectionBox.style.height = '0px';
        selectionBox.style.display = 'block';
    });

    cameraWrapper.addEventListener('mousemove', (e) => {
        if (!isSelecting) return;
        e.preventDefault();

        const rect = cameraWrapper.getBoundingClientRect();
        let currentX = e.clientX - rect.left;
        let currentY = e.clientY - rect.top;

        // 优化：正确处理所有拖拽方向
        const newX = Math.min(currentX, startX);
        const newY = Math.min(currentY, startY);
        const newW = Math.abs(currentX - startX);
        const newH = Math.abs(currentY - startY);

        selectionBox.style.left = newX + 'px';
        selectionBox.style.top = newY + 'px';
        selectionBox.style.width = newW + 'px';
        selectionBox.style.height = newH + 'px';
    });

    // 修正：在 window 上监听 mouseup，防止鼠标在图像外松开导致失败
    window.addEventListener('mouseup', (e) => {
        if (!isSelecting || e.button !== 0) return;
        e.preventDefault();

        isSelecting = false;
        selectionBox.style.display = 'none';
        cameraWrapper.style.cursor = 'default';

        const finalRect = {
            x: parseFloat(selectionBox.style.left),
            y: parseFloat(selectionBox.style.top),
            w: parseFloat(selectionBox.style.width),
            h: parseFloat(selectionBox.style.height)
        };

        if (finalRect.w > 10 && finalRect.h > 10) {
            // 坐标转换逻辑保持不变，但现在基准更准确了
            const scaleX = cameraFeed.naturalWidth / cameraFeed.clientWidth;
            const scaleY = cameraFeed.naturalHeight / cameraFeed.clientHeight;

            const backendRect = {
                x: Math.round(finalRect.x * scaleX),
                y: Math.round(finalRect.y * scaleY),
                w: Math.round(finalRect.w * scaleX),
                h: Math.round(finalRect.h * scaleY)
            };
            startTracking(backendRect);
        }
    });

    // 增加 mouseleave 事件处理，防止鼠标移出时状态错误
    cameraWrapper.addEventListener('mouseleave', () => {
        if (isSelecting) {
            isSelecting = false;
            selectionBox.style.display = 'none';
            cameraWrapper.style.cursor = 'default';
        }
    });

    function startTracking(rect) {
        fetch('/api/start_tracking', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rect: rect })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    isTracking = true;
                    btnStart.style.display = 'none';
                    btnStop.style.display = 'block';
                    console.log('追踪已启动!');
                } else {
                    alert('启动追踪失败: ' + data.message);
                }
            });
    }

    function stopTracking() {
        fetch('/api/stop_tracking', { method: 'POST' })
            .then(() => {
                isTracking = false;
                btnStart.style.display = 'block';
                btnStop.style.display = 'none';
                console.log('追踪已停止。');
            });
    }
}