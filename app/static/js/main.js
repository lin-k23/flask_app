// 导入各个初始化函数
import { initDetection } from './modules/detection.js';
import { initCarControls } from './modules/car.js';
import { initArm } from './modules/arm.js';
import { initSystemControls } from './modules/system.js';
import { initPegboard } from './modules/pegboard.js';
import { initTracking } from './modules/tracking.js';
import { initStateManager } from './modules/stateManager.js';
import { initThemeSwitcher } from './modules/theme.js';
// --- [核心修改] 导入新的Task1队列模块 ---
import { initTask1Queue } from './modules/task1_queue.js';

// 监听'DOMContentLoaded'事件，确保在整个HTML页面都准备好之后再执行代码
document.addEventListener('DOMContentLoaded', function () {
    console.log("主程序启动，开始初始化所有模块...");
    initDetection();
    initCarControls();
    initArm();
    initSystemControls();
    initPegboard();
    initTracking();
    initStateManager();
    initThemeSwitcher();
    // --- [核心修改] 初始化Task1队列模块 ---
    initTask1Queue();
    console.log("所有模块已初始化。");
});