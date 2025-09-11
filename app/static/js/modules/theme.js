export function initThemeSwitcher() {
    const switcher = document.getElementById('theme-switcher');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');

    if (!switcher || !sunIcon || !moonIcon) {
        console.error('Theme switcher elements not found!');
        return;
    }

    // 通过在 body 上切换 class 来应用主题
    function applyTheme(theme) {
        if (theme === 'light') {
            document.body.classList.add('light-theme');
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
            localStorage.setItem('theme', 'light');
        } else {
            document.body.classList.remove('light-theme');
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
            localStorage.setItem('theme', 'dark');
        }
    }

    // 为按钮添加点击事件
    switcher.addEventListener('click', () => {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        if (currentTheme === 'dark') {
            applyTheme('light');
        } else {
            applyTheme('dark');
        }
    });

    // 页面加载时应用保存的主题
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        applyTheme(savedTheme);
    } else {
        applyTheme('dark'); // 默认为深色主题
    }
}