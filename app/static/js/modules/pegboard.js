// app/static/js/modules/pegboard.js (最终修正版)

export function initPegboard() {
    const rows = 8, cols = 15;
    const isHole = () => true;

    let board = Array.from({ length: rows }, () => Array.from({ length: cols }, () => 0));

    const root = document.getElementById("pegboard");
    const tools = document.getElementById("peg-tools");
    const coordDisplay = document.getElementById("peg-coord");

    // --- [核心修改] 移除对 visionLogEl 的获取和直接操作 ---

    if (!root || !tools || !coordDisplay) {
        console.error("Pegboard module is missing required elements.");
        return;
    }

    const HOOK_TYPES = ["h1", "h2", "h3", "h4"];
    let currentType = "h1";

    tools.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        currentType = btn.dataset.type;
        tools.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    });

    // ... (键盘事件监听不变) ...
    window.addEventListener("keydown", (e) => {
        const key = e.key;
        let targetType = null;
        if (key >= "1" && key <= "4") {
            targetType = `h${key}`;
        } else if (key === "0" || key === "Backspace" || key === "Delete") {
            targetType = "erase";
        }
        if (targetType) {
            currentType = targetType;
            tools.querySelectorAll("button").forEach(b => {
                b.classList.toggle("active", b.dataset.type === targetType);
            });
        }
    });


    // --- [核心修改] 简化发送函数，不再操作UI ---
    function sendPegboardTarget(row, col) {
        fetch("/api/send_pegboard_target", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row: row, col: col })
        })
            .then(res => res.json())
            .then(data => {
                // 只在控制台打印响应，UI日志会自动更新
                console.log("Pegboard target sent response:", data);
            })
            .catch(error => {
                console.error("发送洞洞板坐标失败:", error);
            });
    }

    // ... (paintHole, syncToBackend, renderBoard 等函数不变, renderBoard内部的handlePaint逻辑也不变) ...
    function paintHole(element, state) {
        element.classList.toggle("active", !!state && state !== 0);
        HOOK_TYPES.forEach(type => element.classList.remove(type));
        if (state && typeof state === 'string') {
            element.dataset.t = state;
            element.classList.add(state);
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
                        if (newState !== 0) {
                            sendPegboardTarget(r, c);
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

    // ... (初始化 fetch 不变) ...
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