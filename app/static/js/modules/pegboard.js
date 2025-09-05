export function initPegboard() {
    const rows = 10, cols = 15;
    const isHole = (r, c) => (r === 0 || r === rows - 1) ? (c >= 3 && c <= 11) : (c >= 0 && c < cols);

    // 状态：null = 无孔；0 = 空；'h1' | 'h2' | 'h3' | 'h4'
    let board = Array.from({ length: rows }, (_, r) =>
        Array.from({ length: cols }, (_, c) => (isHole(r, c) ? 0 : null))
    );

    const root = document.getElementById("pegboard");
    const tools = document.getElementById("peg-tools");
    const coord = document.getElementById("peg-coord");
    if (!root) return;

    const TYPES = ["h1", "h2", "h3", "h4"];
    let currentType = "h1";

    // 工具条
    tools?.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        tools.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentType = btn.dataset.type; // h1/h2/h3/h4/erase
    });

    // 快捷键 1~4 选择钩子，0/Backspace 清除
    window.addEventListener("keydown", (e) => {
        const k = e.key;
        if (k >= "1" && k <= "4") {
            currentType = TYPES[Number(k) - 1];
            tools?.querySelectorAll("button").forEach(b => {
                b.classList.toggle("active", b.dataset.type === currentType);
            });
        } else if (k === "0" || k === "Backspace") {
            currentType = "erase";
            tools?.querySelectorAll("button").forEach(b => {
                b.classList.toggle("active", b.dataset.type === "erase");
            });
        }
    });

    function paint(el, val) {
        el.classList.toggle("active", !!val && val !== 0);
        if (val && val !== 0) el.dataset.t = val; else el.removeAttribute("data-t");
    }

    function render() {
        root.innerHTML = "";
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                if (!isHole(r, c)) {
                    const s = document.createElement("div");
                    s.className = "spacer";
                    root.appendChild(s);
                    continue;
                }
                const h = document.createElement("div");
                h.className = "hole";
                h.dataset.r = r; h.dataset.c = c;
                paint(h, board[r][c]);

                h.addEventListener("mouseenter", () => { coord && (coord.textContent = `${r} , ${c}`); });
                h.addEventListener("mouseleave", () => { coord && (coord.textContent = "– , –"); });

                // 左键放置/切换；右键清除
                h.addEventListener("click", () => {
                    board[r][c] = (currentType === "erase") ? 0 : currentType;
                    paint(h, board[r][c]);
                    sync(r, c, board[r][c]);
                });
                h.addEventListener("contextmenu", (e) => {
                    e.preventDefault();
                    board[r][c] = 0; paint(h, 0); sync(r, c, 0);
                });

                root.appendChild(h);
            }
        }
    }

    // 同步到后端
    function sync(r, c, state) {
        fetch("/api/pegboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row: r, col: c, state })
        }).catch(console.error);
    }

    // 初始化：兼容老数据(0/1或数字1~4)
    fetch("/api/pegboard")
        .then(res => res.ok ? res.json() : Promise.reject(res.status))
        .then(data => {
            if (Array.isArray(data) && data.length) {
                board = data.map(row => row.map(v => {
                    if (v === null) return null;
                    if (v === 0 || v === "0") return 0;
                    if (typeof v === "string" && TYPES.includes(v)) return v;
                    if (typeof v === "number" && v >= 1 && v <= 4) return TYPES[v - 1];
                    if (v === 1 || v === "1") return "h1";
                    return 0;
                }));
            }
            render();
        })
        .catch(() => render());
}
