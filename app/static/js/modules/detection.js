// app/static/js/modules/detection.js

export function initDetection() {
    // 获取所有需要更新数据的UI元素
    const colorBlockDataEl = document.getElementById('color-block-data');
    const apriltagDataEl = document.getElementById('apriltag-data');
    const yoloDataEl = document.getElementById('yolo-data');
    const nanotrackDataEl = document.getElementById('nanotrack-data'); // <--- 新增
    const qrcodeDataEl = document.getElementById('qrcode-data'); // <--- 新增

    // 获取所有功能开关
    const blobToggleSwitch = document.getElementById('toggle-blob-switch');
    const qrcodeToggleSwitch = document.getElementById('toggle-qrcode-switch'); // <--- 新增

    // 统一处理开关事件的函数
    function setupSwitchListener(switchElement, featureName) {
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
                    // 根据开关和特性名称更新UI
                    if (featureName === 'color_block') {
                        updateUiState(colorBlockDataEl, isEnabled);
                    } else if (featureName === 'qrcode') {
                        updateUiState(qrcodeDataEl, isEnabled);
                    }
                });
        });
    }

    // 设置色块检测和二维码识别的开关
    setupSwitchListener(blobToggleSwitch, 'color_block');
    setupSwitchListener(qrcodeToggleSwitch, 'qrcode');

    // 通用的UI状态更新函数
    function updateUiState(element, isEnabled, defaultText = '等待数据...') {
        if (isEnabled) {
            element.textContent = defaultText;
            element.style.opacity = '1';
        } else {
            element.textContent = '已禁用';
            element.style.opacity = '0.5';
        }
    }

    // 美化JSON字符串显示的辅助函数
    function formatJsonPayload(payload) {
        try {
            const data = JSON.parse(payload);
            return Object.entries(data)
                .map(([key, value]) => `${key}: ${value}`)
                .join('\n');
        } catch (e) {
            // 如果不是有效的JSON，直接返回原始字符串
            return payload;
        }
    }

    // 主数据获取与渲染函数
    function fetchDetectionData() {
        fetch('/api/detection_data')
            .then(response => response.ok ? response.json() : Promise.reject('Network error'))
            .then(data => {
                // 更新NanoTrack追踪数据
                if (data.nanotrack && data.nanotrack.detected) {
                    const track = data.nanotrack;
                    nanotrackDataEl.textContent = `状态: ${track.status}\n置信度: ${track.score}\nx: ${track.x}, y: ${track.y}, w: ${track.w}, h: ${track.h}`;
                    nanotrackDataEl.style.color = '#4CAF50'; // 追踪时显示为绿色
                } else {
                    nanotrackDataEl.textContent = '未在追踪';
                    nanotrackDataEl.style.color = 'inherit';
                }

                // 更新色块数据
                if (blobToggleSwitch.checked) {
                    if (data.color_block && data.color_block.detected) {
                        const cb = data.color_block;
                        colorBlockDataEl.textContent = `offset_x: ${cb.offset_x}, offset_y: ${cb.offset_y}\nw: ${cb.w}, h: ${cb.h}, angle: ${cb.angle.toFixed(1)}`;
                    } else {
                        colorBlockDataEl.textContent = '未检测到';
                    }
                }

                // 更新AprilTag数据
                if (data.apriltag && data.apriltag.detected) {
                    const tag = data.apriltag;
                    apriltagDataEl.textContent = `id: ${tag.id}\noffset_x: ${tag.offset_x}, offset_y: ${tag.offset_y}\ndistance: ${tag.distance}`;
                } else {
                    apriltagDataEl.textContent = '未检测到';
                }

                // 更新YOLOv5数据
                if (data.yolo_objects && data.yolo_objects.detected) {
                    let yoloPanelText = data.yolo_objects.objects.map(obj =>
                        `标签: ${obj.label}, 置信度: ${obj.score}\n  └─ offset_x:${obj.offset_x}, offset_y:${obj.offset_y}`
                    ).join('\n');
                    yoloDataEl.textContent = yoloPanelText;
                } else {
                    yoloDataEl.textContent = '未检测到目标';
                }

                // 更新二维码数据
                if (qrcodeToggleSwitch.checked) {
                    if (data.qrcode && data.qrcode.detected) {
                        qrcodeDataEl.textContent = formatJsonPayload(data.qrcode.payload);
                    } else {
                        qrcodeDataEl.textContent = '未检测到';
                    }
                }

            })
            .catch(error => {
                console.error('获取检测数据失败:', error);
                // 统一显示API错误
                [colorBlockDataEl, apriltagDataEl, yoloDataEl, nanotrackDataEl, qrcodeDataEl].forEach(el => {
                    el.textContent = 'API错误';
                });
            });
    }

    // 初始化UI状态并定时刷新
    setInterval(fetchDetectionData, 200);
    updateUiState(colorBlockDataEl, blobToggleSwitch.checked);
    updateUiState(qrcodeDataEl, qrcodeToggleSwitch.checked);
}