// app/static/js/modules/detection.js

export function initDetection() {
    // ... (获取UI元素和颜色映射的代码不变) ...
    const colorBlockDataEl = document.getElementById('color-block-data');
    const apriltagDataEl = document.getElementById('apriltag-data');
    const nanotrackDataEl = document.getElementById('nanotrack-data');
    const qrcodeDataEl = document.getElementById('qrcode-data');
    const nanotrackPanel = document.getElementById('nanotrack-panel');
    const blobToggleSwitch = document.getElementById('toggle-blob-switch');
    const qrcodeToggleSwitch = document.getElementById('toggle-qrcode-switch');
    const blobColorSelect = document.getElementById('blob-color-select');

    const COLOR_HEX_MAP = {
        "blue": "#60a5fa", "yellow": "#facc15", "orange": "#fb923c", "purple": "#a78bfa",
    };

    function updateSelectBackground(selectElement) {
        const selectedColor = selectElement.value;
        const colorHex = COLOR_HEX_MAP[selectedColor];
        if (colorHex) {
            selectElement.style.backgroundImage = `url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="6" fill="${colorHex.replace("#", "%23")}"/></svg>')`;
        }
    }

    if (blobColorSelect) {
        blobColorSelect.addEventListener('change', function () {
            const selectedColor = this.value;
            // --- [核心修改] 颜色选择现在触发 Task 1 的抓取指令 ---
            fetch('/api/execute_task1_grab', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ color: selectedColor }), // 发送颜色信息
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status !== 'success') {
                        alert(`指令发送失败: ${data.message}`);
                    }
                    console.log('Task 1 Grab command response:', data.message)
                })
                .catch(err => console.error('Failed to send Task 1 grab command:', err));

            // 同时，仍然更新后台视觉算法的目标颜色
            fetch('/api/set_blob_color', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ color: selectedColor }),
            });

            updateSelectBackground(this);
        });
        updateSelectBackground(blobColorSelect);
    }

    // ... (其他函数如 setupSwitchListener, fetchDetectionData 等保持不变) ...
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