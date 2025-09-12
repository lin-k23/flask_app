// app/static/js/modules/detection.js

export function initDetection() {
    // 获取所有需要的UI元素
    const colorBlockDataEl = document.getElementById('color-block-data');
    const apriltagDataEl = document.getElementById('apriltag-data');
    const nanotrackDataEl = document.getElementById('nanotrack-data');
    const qrcodeDataEl = document.getElementById('qrcode-data');
    const nanotrackPanel = document.getElementById('nanotrack-panel');
    const blobToggleSwitch = document.getElementById('toggle-blob-switch');
    const qrcodeToggleSwitch = document.getElementById('toggle-qrcode-switch');
    const blobColorSelect = document.getElementById('blob-color-select');
    const blobColorSelectWrapper = document.getElementById('blob-color-select-wrapper');
    const executeTask1Btn = document.getElementById('btn-execute-task1');

    const COLOR_HEX_MAP = {
        "blue": "#60a5fa", "yellow": "#facc15", "orange": "#fb923c", "purple": "#a78bfa",
    };

    // 这个函数负责更新UI
    function updateSelectBackground(selectElement) {
        const selectedColor = selectElement.value;
        const colorHex = COLOR_HEX_MAP[selectedColor];

        if (colorHex && blobColorSelectWrapper) {
            // [需求 2] 将背景颜色应用到父容器上
            blobColorSelectWrapper.style.backgroundColor = colorHex;

            // 更新文字颜色以保证可读性
            selectElement.style.color = '#1a202c';

            // [需求 1] 移除背景小圆点图标
            selectElement.style.backgroundImage = 'none';
        }
    }

    if (blobColorSelect) {
        // 为下拉框的 'change' 事件添加监听器
        blobColorSelect.addEventListener('change', function () {
            // 当用户选择新颜色时，立刻调用函数更新背景色
            updateSelectBackground(this);

            // 同时，将新选择的颜色通知后端视觉模块
            const selectedColor = this.value;
            fetch('/api/set_blob_color', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ color: selectedColor }),
            });
        });

        // 在页面加载时，立即调用一次以设置初始颜色
        updateSelectBackground(blobColorSelect);
    }

    if (executeTask1Btn) {
        // “抓取”按钮的事件监听器保持不变
        executeTask1Btn.addEventListener('click', function () {
            const selectedColor = blobColorSelect.value;
            fetch('/api/execute_task1_grab', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ color: selectedColor }),
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status !== 'success') {
                        alert(`指令发送失败: ${data.message}`);
                    }
                    console.log('Task 1 Grab command response:', data.message)
                })
                .catch(err => console.error('Failed to send Task 1 grab command:', err));
        });
    }

    // (文件的其余部分保持不变)

    function setupSwitchListener(switchElement, featureName) {
        if (!switchElement) return;
        switchElement.addEventListener('change', function () {
            const isEnabled = this.checked;
            fetch('/api/toggle_vision_feature', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ feature: featureName, enabled: isEnabled }),
            })
        });
    }

    setupSwitchListener(blobToggleSwitch, 'color_block');
    setupSwitchListener(qrcodeToggleSwitch, 'qrcode');

    function formatJsonPayload(payload) {
        try {
            const data = JSON.parse(payload);
            return Object.entries(data).map(([key, value]) => `${key}: ${value}`).join('\n');
        } catch (e) { return payload; }
    }

    function fetchDetectionData() {
        fetch('/api/detection_data')
            .then(response => response.ok ? response.json() : Promise.reject('Network error'))
            .then(data => {
                if (nanotrackPanel && nanotrackDataEl) {
                    if (data.nanotrack && data.nanotrack.detected) {
                        const track = data.nanotrack;
                        nanotrackPanel.style.display = 'block';
                        nanotrackDataEl.textContent = `状态: ${track.status}\n置信度: ${track.score}\nx: ${track.x}, y: ${track.y}, w: ${track.w}, h: ${track.h}`;
                    } else {
                        nanotrackPanel.style.display = 'none';
                    }
                }
                if (blobToggleSwitch && colorBlockDataEl && blobToggleSwitch.checked) {
                    if (data.color_block && data.color_block.detected) {
                        const cb = data.color_block;
                        colorBlockDataEl.textContent = `颜色: ${cb.color_name} (索引:${cb.color_index})\noffset_x: ${cb.offset_x}, offset_y: ${cb.offset_y}\nw: ${cb.w}, h: ${cb.h}, angle: ${cb.angle.toFixed(1)}`;
                    } else {
                        colorBlockDataEl.textContent = '未检测到';
                    }
                }
                if (apriltagDataEl) {
                    if (data.apriltag && data.apriltag.detected) {
                        const tag = data.apriltag;
                        apriltagDataEl.textContent = `id: ${tag.id}\noffset_x: ${tag.offset_x}, offset_y: ${tag.offset_y}\ndistance: ${tag.distance}`;
                    } else {
                        apriltagDataEl.textContent = '未检测到';
                    }
                }
                if (qrcodeToggleSwitch && qrcodeDataEl && qrcodeToggleSwitch.checked) {
                    if (data.qrcode && data.qrcode.detected) {
                        qrcodeDataEl.textContent = formatJsonPayload(data.qrcode.payload);
                    } else {
                        qrcodeDataEl.textContent = '未检测到';
                    }
                }
            })
            .catch(error => console.error('获取检测数据失败:', error));
    }
    setInterval(fetchDetectionData, 200);
}