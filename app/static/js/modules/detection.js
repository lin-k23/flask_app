// app/static/js/modules/detection.js (已修复)

export function initDetection() {
    // --- 获取UI元素 ---
    const colorBlockDataEl = document.getElementById('color-block-data');
    const apriltagDataEl = document.getElementById('apriltag-data');
    const yoloDataEl = document.getElementById('yolo-data');
    const nanotrackDataEl = document.getElementById('nanotrack-data');
    const qrcodeDataEl = document.getElementById('qrcode-data');
    const nanotrackPanel = document.getElementById('nanotrack-panel');
    const blobToggleSwitch = document.getElementById('toggle-blob-switch');
    const qrcodeToggleSwitch = document.getElementById('toggle-qrcode-switch');

    // 开关控制逻辑
    function setupSwitchListener(switchElement, featureName) {
        if (!switchElement) return; // 增加健壮性
        switchElement.addEventListener('change', function () {
            const isEnabled = this.checked;
            fetch('/api/toggle_vision_feature', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ feature: featureName, enabled: isEnabled }),
            })
                .then(res => res.json())
                .then(data => {
                    console.log(data.message);
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

    // UI状态更新函数
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

    // 主数据获取与渲染函数
    function fetchDetectionData() {
        fetch('/api/detection_data')
            .then(response => response.ok ? response.json() : Promise.reject('Network error'))
            .then(data => {
                // NanoTrack 更新
                if (nanotrackPanel && nanotrackDataEl) {
                    if (data.nanotrack && data.nanotrack.detected) {
                        const track = data.nanotrack;
                        nanotrackPanel.style.display = 'block';
                        nanotrackDataEl.textContent = `状态: ${track.status}\n置信度: ${track.score}\nx: ${track.x}, y: ${track.y}, w: ${track.w}, h: ${track.h}`;
                    } else {
                        nanotrackPanel.style.display = 'none';
                    }
                }

                // 色块数据更新
                if (blobToggleSwitch && colorBlockDataEl && blobToggleSwitch.checked) {
                    if (data.color_block && data.color_block.detected) {
                        const cb = data.color_block;
                        colorBlockDataEl.textContent = `offset_x: ${cb.offset_x}, offset_y: ${cb.offset_y}\nw: ${cb.w}, h: ${cb.h}, angle: ${cb.angle.toFixed(1)}`;
                    } else {
                        colorBlockDataEl.textContent = '未检测到';
                    }
                }

                // AprilTag 更新
                if (apriltagDataEl) {
                    if (data.apriltag && data.apriltag.detected) {
                        const tag = data.apriltag;
                        apriltagDataEl.textContent = `id: ${tag.id}\noffset_x: ${tag.offset_x}, offset_y: ${tag.offset_y}\ndistance: ${tag.distance}`;
                    } else {
                        apriltagDataEl.textContent = '未检测到';
                    }
                }

                // YOLO 更新
                if (yoloDataEl) {
                    yoloDataEl.textContent = '未检测到目标'; // 因为YOLO已禁用
                }

                // QR码 更新
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

    // 初始化
    setInterval(fetchDetectionData, 200);
    updateUiState(colorBlockDataEl, blobToggleSwitch ? blobToggleSwitch.checked : false);
    updateUiState(qrcodeDataEl, qrcodeToggleSwitch ? qrcodeToggleSwitch.checked : false);
}