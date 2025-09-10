// app/static/js/modules/detection.js

export function initDetection() {
    // --- 获取UI元素 ---
    const colorBlockDataEl = document.getElementById('color-block-data');
    const apriltagDataEl = document.getElementById('apriltag-data');
    const nanotrackDataEl = document.getElementById('nanotrack-data');
    const qrcodeDataEl = document.getElementById('qrcode-data');
    const nanotrackPanel = document.getElementById('nanotrack-panel');
    const blobToggleSwitch = document.getElementById('toggle-blob-switch');
    const qrcodeToggleSwitch = document.getElementById('toggle-qrcode-switch');
    const blobColorSelect = document.getElementById('blob-color-select');

    // --- [新增] 定义颜色到CSS颜色的映射 ---
    const COLOR_HEX_MAP = {
        "blue": "#60a5fa",
        "yellow": "#facc15",
        "orange": "#fb923c",
        "purple": "#a78bfa",
    };

    // --- [新增] 更新下拉框背景色的函数 ---
    function updateSelectBackground(selectElement) {
        const selectedColor = selectElement.value;
        const colorHex = COLOR_HEX_MAP[selectedColor];
        if (colorHex) {
            // 使用内联样式来动态改变背景（小圆点）
            selectElement.style.backgroundImage = `url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="6" fill="${colorHex.replace("#", "%23")}"/></svg>')`;
        }
    }

    if (blobColorSelect) {
        blobColorSelect.addEventListener('change', function () {
            const selectedColor = this.value;
            fetch('/api/set_blob_color', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ color: selectedColor }),
            })
                .then(res => res.json())
                .then(data => console.log(data.message))
                .catch(err => console.error('Failed to set blob color:', err));
            updateSelectBackground(this);
        });
        updateSelectBackground(blobColorSelect);
    }

    function setupSwitchListener(switchElement, featureName) {
        if (!switchElement) return;
        switchElement.addEventListener('change', function () {
            const isEnabled = this.checked;
            fetch('/api/toggle_vision_feature', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ feature: featureName, enabled: isEnabled }),
            })
                .then(res => res.json())
                .then(data => {
                    if (featureName === 'color_block') {
                        updateUiState(colorBlockDataEl, isEnabled);
                    } else if (featureName === 'qrcode') {
                        updateUiState(qrcodeDataEl, isEnabled);
                    }
                });
        });
    }

    setupSwitchListener(blobToggleSwitch, 'color_block');
    setupSwitchListener(qrcodeToggleSwitch, 'qrcode');

    function updateUiState(element, isEnabled, defaultText = '等待数据...') {
        if (!element) return;
        const parentBox = element.closest('.data-box');
        if (!parentBox) return;

        if (isEnabled) {
            element.textContent = defaultText;
            parentBox.style.opacity = '1';
        } else {
            element.textContent = '已禁用';
            parentBox.style.opacity = '0.5';
        }
    }

    function formatJsonPayload(payload) {
        try {
            const data = JSON.parse(payload);
            return Object.entries(data)
                .map(([key, value]) => `${key}: ${value}`)
                .join('\n');
        } catch (e) {
            return payload;
        }
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
    updateUiState(colorBlockDataEl, blobToggleSwitch ? blobToggleSwitch.checked : false);
    updateUiState(qrcodeDataEl, qrcodeToggleSwitch ? qrcodeToggleSwitch.checked : false);
}