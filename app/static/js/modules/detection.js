// --- Part 2: Detection Data Logic ---

// 使用 export 将函数暴露出去，以便其他文件可以导入
export function initDetection() {
    const colorBlockDataEl = document.getElementById('color-block-data');
    const apriltagDataEl = document.getElementById('apriltag-data');

    function fetchDetectionData() {
        fetch('/api/detection_data')
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应错误');
                }
                return response.json();
            })
            .then(data => {
                // 更新色块数据
                if (data.color_block && data.color_block.detected) {
                    const cb = data.color_block;
                    colorBlockDataEl.textContent = `x: ${cb.x}, y: ${cb.y}\nw: ${cb.w}, h: ${cb.h}`;
                } else {
                    colorBlockDataEl.textContent = '未检测到';
                }

                // 更新AprilTag数据
                if (data.apriltag && data.apriltag.detected) {
                    const tag = data.apriltag;
                    apriltagDataEl.textContent = `id: ${tag.id}\nx: ${tag.x}, y: ${tag.y}`;
                } else {
                    apriltagDataEl.textContent = '未检测到';
                }
            })
            .catch(error => {
                console.error('获取检测数据失败:', error);
                colorBlockDataEl.textContent = 'API错误';
                apriltagDataEl.textContent = 'API错误';
            });
    }

    // 每200毫秒获取一次数据
    setInterval(fetchDetectionData, 200);
}
