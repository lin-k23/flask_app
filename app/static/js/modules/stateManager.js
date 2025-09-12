// app/static/js/modules/stateManager.js

const MANAGED_COMPONENTS = {
    carControls: document.querySelector('.panel-car-control'),
    pegboard: document.getElementById('pegboard-module'),
    systemSim: document.querySelector('.panel-system-controls'),
};

function updateUiLockState(status) {
    const isManual = status === 'MANUAL';
    const isAwaitingInput = status === 'AWAITING_TASK2_INPUT';

    // 锁定/解锁小车控制
    if (MANAGED_COMPONENTS.carControls) {
        const fieldset = MANAGED_COMPONENTS.carControls.querySelector('.main-controls');
        if (fieldset) fieldset.disabled = !isManual;
    }

    // --- [核心修改] 根据新状态锁定/解锁洞洞板 ---
    if (MANAGED_COMPONENTS.pegboard) {
        const pegboardRoot = MANAGED_COMPONENTS.pegboard.querySelector('#pegboard');
        // 只有在等待输入时才解锁
        if (pegboardRoot) pegboardRoot.classList.toggle('disabled', !isAwaitingInput);
    }

    // [核心修改] 模拟按钮不再被禁用
    if (MANAGED_COMPONENTS.systemSim) {
        const btnSim1 = MANAGED_COMPONENTS.systemSim.querySelector('#btn-simulate-task1');
        const btnSim2 = MANAGED_COMPONENTS.systemSim.querySelector('#btn-simulate-task2');
        if (btnSim1) btnSim1.disabled = false;
        if (btnSim2) btnSim2.disabled = false;
    }

    // 更新标题状态
    const header = document.querySelector('header h1');
    if (header) {
        if (isAwaitingInput) {
            header.textContent = "MaixPy 集成控制面板 (请在洞洞板上选择Task2的目标点)";
            header.style.color = "#00aaff"; // 蓝色提示
        } else if (status === 'TASK_AUTO') {
            header.textContent = "MaixPy 集成控制面板 (自动任务执行中...)";
            header.style.color = "#ff9800";
        } else {
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
    setInterval(fetchSystemStatus, 1000);
}