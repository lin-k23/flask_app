// app/static/js/modules/pegboard.js

export function initPegboard() {
    const rows = 8, cols = 15;
    const root = document.getElementById("pegboard");
    const tools = document.getElementById("peg-tools");
    const coordDisplay = document.getElementById("peg-coord");

    if (!root || !tools || !coordDisplay) {
        console.error("Pegboard module is missing required elements.");
        return;
    }

    // --- [核心修改] 颜色名称到ID的映射，与 vision.py 保持一致 ---
    const COLOR_MAP = {
        "blue": 0,
        "yellow": 1,
        "orange": 2,
        "purple": 3,
    };
    // 用于UI显示的颜色类型
    const COLOR_TYPES = ["blue", "yellow", "orange", "purple"];

    let board = Array.from({ length: rows }, () => Array(cols).fill(0));
    let currentType = "blue"; // 默认选择蓝色

    tools.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        currentType = btn.dataset.type;
        tools.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    });

    // --- [核心修改] 此函数现在是执行Task2的唯一入口 ---
    function executeTask2(row, col) {
        const colorId = COLOR_MAP[currentType];

        if (colorId === undefined) {
            alert(`错误：未知的颜色类型 '${currentType}'`);
            return;
        }

        fetch("/api/execute_task2", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row: row, col: col, color_id: colorId })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status !== 'success') {
                    alert(data.message);
                }
                console.log("Execute Task 2 response:", data)
            })
            .catch(error => console.error("执行Task 2失败:", error));
    }

    function paintHole(element, state) {
        element.classList.toggle("active", !!state && state !== 0);
        // 移除所有颜色相关的class
        COLOR_TYPES.forEach(type => element.classList.remove(type));

        if (state && typeof state === 'string') {
            element.dataset.t = state;
            if (COLOR_TYPES.includes(state)) {
                element.classList.add(state); // 添加对应的颜色class
            }
        } else {
            element.removeAttribute("data-t");
        }
    }

    function syncToBackend(r, c, state) {
        fetch("/api/pegboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row: r, col: c, state: state })
        }).catch(console.error);
    }

    function renderBoard() {
        root.innerHTML = "";
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const hole = document.createElement("div");
                hole.className = "hole";
                hole.dataset.r = r;
                hole.dataset.c = c;
                paintHole(hole, board[r][c]);

                hole.addEventListener("mouseenter", () => { coordDisplay.textContent = `${r} , ${c}`; });

                const handlePaint = () => {
                    const newState = (currentType === "erase") ? 0 : currentType;
                    const oldState = board[r][c];
                    if (newState !== oldState) {
                        board[r][c] = newState;
                        paintHole(hole, newState);
                        syncToBackend(r, c, newState);
                        // --- [核心修改] 点击后直接执行Task 2 ---
                        if (newState !== 0) {
                            executeTask2(r, c);
                        }
                    }
                };

                hole.addEventListener("click", handlePaint);
                hole.addEventListener("contextmenu", (e) => {
                    e.preventDefault();
                    if (board[r][c] !== 0) {
                        board[r][c] = 0;
                        paintHole(hole, 0);
                        syncToBackend(r, c, 0);
                    }
                });

                root.appendChild(hole);
            }
        }
        root.addEventListener("mouseleave", () => { coordDisplay.textContent = `– , –`; });
    }

    fetch("/api/pegboard")
        .then(res => res.ok ? res.json() : Promise.reject(res.status))
        .then(initialBoardState => {
            if (Array.isArray(initialBoardState) && initialBoardState.length === rows) {
                board = initialBoardState;
            }
            renderBoard();
        })
        .catch(() => {
            console.error("Failed to load initial pegboard state. Rendering an empty board.");
            renderBoard();
        });
}