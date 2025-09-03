// 导入各个初始化函数
import { initDetection } from './modules/detection.js';
import { initTrajectory } from './modules/trajectory.js';
import { initArm } from './modules/arm.js';

// 监听'DOMContentLoaded'事件，确保在整个HTML页面都准备好之后再执行代码
document.addEventListener('DOMContentLoaded', function () {
    console.log("主程序启动，开始初始化所有模块...");
    initDetection();
    initTrajectory();
    initArm();
    console.log("所有模块已初始化。");
});
