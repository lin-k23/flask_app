// app/static/js/modules/task1_queue.js

export function initTask1Queue() {
    const task1Tools = document.getElementById('task1-tools');
    const queueList = document.getElementById('task1-queue-list');
    const queueCount = document.getElementById('task1-queue-count');
    const executeBtn = document.getElementById('btn-execute-task1-sequence');
    const clearBtn = document.getElementById('btn-clear-task1-queue');

    if (!task1Tools || !queueList || !executeBtn || !clearBtn) {
        console.warn("Task 1 Queue module elements not found. Skipping initialization.");
        return;
    }

    const COLOR_MAP = {
        "blue": 0, "yellow": 1, "orange": 2, "purple": 3,
    };

    let taskQueue = [];

    function renderQueue() {
        queueList.innerHTML = "";
        if (taskQueue.length === 0) {
            queueList.innerHTML = "<li>队列为空...</li>";
        } else {
            taskQueue.forEach((task, index) => {
                const li = document.createElement("li");
                li.innerHTML = `
                    <span>抓取任务 ${index + 1}: <b>${task.color_name.toUpperCase()}</b></span>
                    <button class="btn-remove-task" data-index="${index}">×</button>
                `;
                li.style.borderLeft = `4px solid var(--chip-${task.color_name}, #fff)`;
                queueList.appendChild(li);
            });
        }
        queueCount.textContent = taskQueue.length;
        executeBtn.disabled = taskQueue.length === 0;
    }

    task1Tools.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;

        const colorType = btn.dataset.type;
        const colorId = COLOR_MAP[colorType];

        if (colorId !== undefined) {
            taskQueue.push({ color_id: colorId, color_name: colorType });
            renderQueue();
        }
    });

    queueList.addEventListener('click', function (e) {
        if (e.target.classList.contains('btn-remove-task')) {
            const index = parseInt(e.target.dataset.index, 10);
            taskQueue.splice(index, 1);
            renderQueue();
        }
    });

    executeBtn.addEventListener("click", () => {
        if (taskQueue.length === 0) return;

        // 假设Task 1启动不需要等待小车信号，直接由用户触发
        fetch("/api/execute_task1_sequence", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tasks: taskQueue })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert("抓取序列已成功启动！");
                    taskQueue = [];
                    renderQueue();
                } else {
                    alert(`启动失败: ${data.message}`);
                }
            })
            .catch(error => console.error("执行Task 1序列失败:", error));
    });

    clearBtn.addEventListener("click", () => {
        taskQueue = [];
        renderQueue();
    });

    renderQueue(); // Initial render
}