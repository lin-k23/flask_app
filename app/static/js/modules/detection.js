// app/static/js/modules/detection.js

export function initDetection() {
    // 获取所有需要更新数据的UI元素
    const colorBlockDataEl = document.getElementById('color-block-data');
    const apriltagDataEl = document.getElementById('apriltag-data');
    const yoloDataEl = document.getElementById('yolo-data');
    const yoloOverlayEl = document.getElementById('yolo-overlay-info');
    const blobToggleSwitch = document.getElementById('toggle-blob-switch');

    // 为色块检测开关添加事件监听器
    blobToggleSwitch.addEventListener('change', function () {
        const isEnabled = this.checked;
        fetch('/api/toggle_vision_feature', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feature: 'color_block', enabled: isEnabled }),
        })
            .then(res => res.json())
            .then(data => {
                console.log(data.message);
                updateBlobUiState(isEnabled);
            });
    });

    // 更新色块检测UI状态的辅助函数
    function updateBlobUiState(isEnabled) {
        if (isEnabled) {
            colorBlockDataEl.textContent = '等待数据...';
            colorBlockDataEl.style.opacity = '1';
        } else {
            colorBlockDataEl.textContent = '已禁用';
            colorBlockDataEl.style.opacity = '0.5';
        }
    }

    // 主数据获取与渲染函数
    function fetchDetectionData() {
        fetch('/api/detection_data')
            .then(response => response.ok ? response.json() : Promise.reject('Network error'))
            .then(data => {
                // 更新色块数据UI
                if (blobToggleSwitch.checked) {
                    if (data.color_block && data.color_block.detected) {
                        const cb = data.color_block;
                        colorBlockDataEl.textContent = `offset_x: ${cb.offset_x}, offset_y: ${cb.offset_y}\nw: ${cb.w}, h: ${cb.h}, angle: ${cb.angle.toFixed(1)}`;
                    } else {
                        colorBlockDataEl.textContent = '未检测到';
                    }
                }

                // 更新AprilTag数据UI
                if (data.apriltag && data.apriltag.detected) {
                    const tag = data.apriltag;
                    apriltagDataEl.textContent = `id: ${tag.id}\noffset_x: ${tag.offset_x}, offset_y: ${tag.offset_y}\ndistance: ${tag.distance}`;
                } else {
                    apriltagDataEl.textContent = '未检测到';
                }

                // --- [核心修正] 更新YOLOv5数据显示 ---
                if (data.yolo_objects && data.yolo_objects.detected) {
                    let yoloPanelText = '';  // 用于检测面板的详细文本
                    let yoloOverlayText = '';// 用于摄像头覆盖层的简洁文本

                    data.yolo_objects.objects.forEach(obj => {
                        // 格式化检测面板的文本，确保包含偏移量
                        yoloPanelText += `标签: ${obj.label}, 置信度: ${obj.score}\n`;
                        yoloPanelText += `  └─ offset_x:${obj.offset_x}, offset_y:${obj.offset_y}\n`;

                        // 格式化摄像头覆盖层的文本，确保包含中心坐标
                        yoloOverlayText += `[${obj.label}: (${obj.center_x}, ${obj.center_y})] `;
                    });

                    yoloDataEl.textContent = yoloPanelText.trim();
                    yoloOverlayEl.textContent = yoloOverlayText.trim();
                } else {
                    yoloDataEl.textContent = '未检测到目标';
                    yoloOverlayEl.textContent = ''; // 如果没有目标，清空覆盖层
                }
            })
            .catch(error => {
                console.error('获取检测数据失败:', error);
                // 确保所有UI都显示错误状态
                colorBlockDataEl.textContent = 'API错误';
                apriltagDataEl.textContent = 'API错误';
                yoloDataEl.textContent = 'API错误';
                yoloOverlayEl.textContent = 'API错误';
            });
    }

    // 初始化UI并定时刷新
    setInterval(fetchDetectionData, 200);
    updateBlobUiState(blobToggleSwitch.checked);
}