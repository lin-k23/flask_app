// app/static/js/modules/pegboard.js (最终修正版)

export function initPegboard() {
    const rows = 8, cols = 15;
    const isHole = () => true; // 所有位置都是孔

    // 状态: 0 = 空; 'h1' | 'h2' | 'h3' | 'h4' = 有钩子
    let board = Array.from({ length: rows }, () => Array.from({ length: cols }, () => 0));

    // 获取所有必要的DOM元素
    const root = document.getElementById("pegboard");
    const tools = document.getElementById("peg-tools");
    const coordDisplay = document.getElementById("peg-coord");

    // 如果关键元素不存在，则不执行任何操作
    if (!root || !tools || !coordDisplay) {
        console.error("Pegboard module is missing required elements.");
        return;
    }

    const HOOK_TYPES = ["h1", "h2", "h3", "h4"];
    let currentType = "h1";

    // --- 事件监听 ---

    // 1. 工具栏点击事件
    tools.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;

        currentType = btn.dataset.type; // h1/h2/h3/h4/erase

        tools.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
    });

    // 2. 键盘快捷键事件
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

    // --- 核心渲染与交互逻辑 ---

    // 根据状态值更新单个孔的样式
    function paintHole(element, state) {
        element.classList.toggle("active", !!state && state !== 0);
        // 移除旧的状态
        HOOK_TYPES.forEach(type => element.classList.remove(type));

        if (state && typeof state === 'string') {
            element.dataset.t = state;
            element.classList.add(state); // 添加对应的class以应用样式
        } else {
            element.removeAttribute("data-t");
        }
    }

    // 向后端同步单个孔的状态
    function syncToBackend(r, c, state) {
        fetch("/api/pegboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row: r, col: c, state: state })
        }).catch(console.error);
    }

    // 完整渲染整个洞洞板
    function renderBoard() {
        root.innerHTML = ""; // 清空面板
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const hole = document.createElement("div");
                hole.className = "hole";
                hole.dataset.r = r;
                hole.dataset.c = c;

                paintHole(hole, board[r][c]);

                // 鼠标悬停显示坐标
                hole.addEventListener("mouseenter", () => { coordDisplay.textContent = `${r} , ${c}`; });

                // 点击放置或擦除
                const handlePaint = () => {
                    const newState = (currentType === "erase") ? 0 : currentType;
                    board[r][c] = newState;
                    paintHole(hole, newState);
                    syncToBackend(r, c, newState);
                };

                hole.addEventListener("click", handlePaint);
                hole.addEventListener("contextmenu", (e) => {
                    e.preventDefault(); // 阻止右键菜单
                    board[r][c] = 0;
                    paintHole(hole, 0);
                    syncToBackend(r, c, 0);
                });

                root.appendChild(hole);
            }
        }
        root.addEventListener("mouseleave", () => { coordDisplay.textContent = `– , –`; });
    }

    // --- 初始化 ---
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