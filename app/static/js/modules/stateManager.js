// app/static/js/modules/stateManager.js

const MANAGED_COMPONENTS = {
    carControls: document.querySelector('.panel-car-control'),
    pegboard: document.getElementById('pegboard-module'),
    systemSim: document.querySelector('.panel-system-controls'),
    btnFinishTask: document.getElementById('btn-finish-task'),
    colorSelect: document.getElementById('blob-color-select'), // Task 1 control
};

function updateUiLockState(status) {
    const isManual = status === 'MANUAL';
    const isTask1Active = status.startsWith('TASK1');
    const isTask2Active = status.startsWith('TASK2');
    const isAwaitingInput = status.endsWith('AWAITING_INPUT');
    const isExecuting = status.endsWith('EXECUTING');

    // --- [核心修改] 根据新的状态模型全面管理UI ---

    // 1. 锁定/解锁小车手动控制
    if (MANAGED_COMPONENTS.carControls) {
        const fieldset = MANAGED_COMPONENTS.carControls.querySelector('.main-controls');
        if (fieldset) fieldset.disabled = !isManual;
    }

    // 2. 锁定/解锁 Task 1 的颜色选择器
    if (MANAGED_COMPONENTS.colorSelect) {
        // 只有在等待Task1输入时才可操作
        MANAGED_COMPONENTS.colorSelect.disabled = !(status === 'TASK1_AWAITING_INPUT');
    }

    // 3. 锁定/解锁 Task 2 的洞洞板
    if (MANAGED_COMPONENTS.pegboard) {
        const pegboardRoot = MANAGED_COMPONENTS.pegboard.querySelector('#pegboard');
        if (pegboardRoot) {
            // 只有在等待Task2输入时才可操作
            pegboardRoot.classList.toggle('disabled', !(status === 'TASK2_AWAITING_INPUT'));
        }
    }

    // 4. 锁定/解锁模拟按钮
    if (MANAGED_COMPONENTS.systemSim) {
        const btnSim1 = MANAGED_COMPONENTS.systemSim.querySelector('#btn-simulate-task1');
        const btnSim2 = MANAGED_COMPONENTS.systemSim.querySelector('#btn-simulate-task2');
        if (btnSim1) btnSim1.disabled = !isManual;
        if (btnSim2) btnSim2.disabled = !isManual;
    }

    // 5. 控制“结束任务”按钮的可见性
    if (MANAGED_COMPONENTS.btnFinishTask) {
        // 在任何一个任务阶段（等待或执行中）都显示
        MANAGED_COMPONENTS.btnFinishTask.style.display = (isTask1Active || isTask2Active) ? 'block' : 'none';
    }

    // 6. 更新标题状态
    const header = document.querySelector('header h1');
    if (header) {
        if (status === 'TASK1_AWAITING_INPUT') {
            header.textContent = "MaixPy 集成控制面板 (Task 1: 请选择要抓取的色块颜色)";
            header.style.color = "#00aaff";
        } else if (status === 'TASK1_EXECUTING') {
            header.textContent = "MaixPy 集成控制面板 (Task 1: 机械臂抓取中...)";
            header.style.color = "#ff9800";
        } else if (status === 'TASK2_AWAITING_INPUT') {
            header.textContent = "MaixPy 集成控制面板 (Task 2: 请在洞洞板上选择目标点)";
            header.style.color = "#00aaff";
        } else if (status === 'TASK2_EXECUTING') {
            header.textContent = "MaixPy 集成控制面板 (Task 2: 机械臂放置中...)";
            header.style.color = "#ff9800";
        } else { // MANUAL
            header.textContent = "MaixPy 集成控制面板";
            header.style.color = "";
        }
    }
}

async function fetchSystemStatus() {
    try {
        const response = await fetch('/api/system_status');
        if (!response.ok) {
            console.error('Failed to fetch system status:', response.status);
            return;
        }
        const data = await response.json();
        updateUiLockState(data.status);
    } catch (error) {
        console.error('Error fetching system status:', error);
    }
}

export function initStateManager() {
    console.log("State Manager initialized.");
    setInterval(fetchSystemStatus, 500); // 提高刷新率以获得更及时的UI更新
}