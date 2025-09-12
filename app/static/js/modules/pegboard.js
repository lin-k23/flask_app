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

    const COLOR_MAP = { "blue": 0, "yellow": 1, "orange": 2, "purple": 3 };
    const COLOR_TYPES = ["blue", "yellow", "orange", "purple"];
    let board = Array.from({ length: rows }, () => Array(cols).fill(0));
    let currentType = "blue";

    tools.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        currentType = btn.dataset.type;
        tools.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    });

    // --- [核心修改] 此函数现在调用新的 Task 2 place API ---
    function executeTask2Place(row, col) {
        if (currentType === "erase") {
            // 如果是擦除模式，则不发送指令
            return;
        }

        const colorId = COLOR_MAP[currentType];
        if (colorId === undefined) {
            alert(`错误：未知的颜色类型 '${currentType}'`);
            return;
        }

        fetch("/api/execute_task2_place", { // API endpoint a fost modificat
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row: row, col: col, color_id: colorId })
        })
            .then(res => res.json())
            .then(data => {
                if (data.status !== 'success') {
                    alert(`指令发送失败: ${data.message}`);
                }
                console.log("Execute Task 2 Place response:", data)
            })
            .catch(error => console.error("执行Task 2失败:", error));
    }

    // ... (函数 paintHole, syncToBackend, renderBoard 保持不变) ...
    function paintHole(element, state) {
        element.classList.toggle("active", !!state && state !== 0);
        COLOR_TYPES.forEach(type => element.classList.remove(type));
        if (state && typeof state === 'string') {
            element.dataset.t = state;
            if (COLOR_TYPES.includes(state)) {
                element.classList.add(state);
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
                    // --- [核心修改] 只有在状态改变时才执行 ---
                    if (newState !== oldState) {
                        board[r][c] = newState;
                        paintHole(hole, newState);
                        syncToBackend(r, c, newState);
                        // 点击后直接执行Task 2 放置指令
                        executeTask2Place(r, c);
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