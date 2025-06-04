// MLB 統計查詢系統 - 主要 JavaScript 檔案

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有功能
    initializeSearch();
    initializeGameUpdates();
    initializeTooltips();
    initializeCharts();
    initializeAIFeatures();
    initializeThemeToggle();

    console.log('MLB 統計查詢系統已載入完成');
});

// 搜尋功能
function initializeSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    
    searchInputs.forEach(input => {
        // 自動完成功能
        let timeout = null;
        
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            const query = this.value;
            
            if (query.length >= 2) {
                timeout = setTimeout(() => {
                    performAutoComplete(query, this);
                }, 300); // 延遲 300ms 避免過多請求
            } else {
                hideAutoComplete();
            }
        });
        
        // 失去焦點時隱藏自動完成
        input.addEventListener('blur', function() {
            setTimeout(hideAutoComplete, 200);
        });
    });
}

// 執行自動完成搜尋
function performAutoComplete(query, inputElement) {
    fetch(`/api/players/search/?q=${encodeURIComponent(query)}&limit=5`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.players.length > 0) {
                showAutoComplete(data.players, inputElement);
            } else {
                hideAutoComplete();
            }
        })
        .catch(error => {
            console.error('自動完成搜尋錯誤:', error);
            hideAutoComplete();
        });
}

// 顯示自動完成建議
function showAutoComplete(players, inputElement) {
    // 移除現有的建議框
    hideAutoComplete();
    
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'autocomplete-suggestions';
    suggestionsDiv.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #ddd;
        border-top: none;
        border-radius: 0 0 5px 5px;
        max-height: 200px;
        overflow-y: auto;
        z-index: 1000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    `;
    
    players.forEach(player => {
        const suggestionDiv = document.createElement('div');
        suggestionDiv.className = 'autocomplete-suggestion';
        suggestionDiv.style.cssText = `
            padding: 10px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: background-color 0.2s;
        `;
        
        suggestionDiv.innerHTML = `
            <strong>${player.fullName}</strong><br>
            <small>${player.currentTeam} - ${player.primaryPosition}</small>
        `;
        
        suggestionDiv.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f9fa';
        });
        
        suggestionDiv.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'white';
        });
        
        suggestionDiv.addEventListener('click', function() {
            window.location.href = `/players/${player.id}/`;
        });
        
        suggestionsDiv.appendChild(suggestionDiv);
    });
    
    const container = inputElement.parentElement;
    container.style.position = 'relative';
    container.appendChild(suggestionsDiv);
}

// 隱藏自動完成建議
function hideAutoComplete() {
    const suggestions = document.querySelector('.autocomplete-suggestions');
    if (suggestions) {
        suggestions.remove();
    }
}

// 比賽資訊即時更新
function initializeGameUpdates() {
    const gameCards = document.querySelectorAll('.game-card');
    
    if (gameCards.length > 0) {
        // 每 5 分鐘更新一次比賽狀態
        setInterval(updateGameStatuses, 5 * 60 * 1000);
    }
}

// 更新比賽狀態
function updateGameStatuses() {
    const today = new Date().toISOString().split('T')[0];
    
    fetch(`/api/games/?date=${today}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateGameCards(data.games);
            }
        })
        .catch(error => {
            console.error('更新比賽狀態錯誤:', error);
        });
}

// 更新比賽卡片
function updateGameCards(games) {
    games.forEach(game => {
        const gameCard = document.querySelector(`[data-game-id="${game.game_pk}"]`);
        if (gameCard) {
            const statusElement = gameCard.querySelector('.game-status');
            const awayScoreElement = gameCard.querySelector('.away-score');
            const homeScoreElement = gameCard.querySelector('.home-score');
            
            if (statusElement) statusElement.textContent = game.status;
            if (awayScoreElement) awayScoreElement.textContent = game.away_team.score;
            if (homeScoreElement) homeScoreElement.textContent = game.home_team.score;
        }
    });
}

// 初始化工具提示
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

// 顯示工具提示
function showTooltip(event) {
    const tooltipText = event.target.getAttribute('data-tooltip');
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 1000;
        pointer-events: none;
        white-space: nowrap;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
}

// 隱藏工具提示
function hideTooltip() {
    const tooltip = document.querySelector('.tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// 初始化圖表
function initializeCharts() {
    const chartContainers = document.querySelectorAll('.chart-container');
    
    chartContainers.forEach(container => {
        const chartType = container.getAttribute('data-chart-type');
        const chartData = JSON.parse(container.getAttribute('data-chart-data') || '{}');
        
        if (chartType && chartData) {
            createChart(container, chartType, chartData);
        }
    });
}

// 建立圖表
function createChart(container, type, data) {
    // 這裡可以使用 Chart.js 或其他圖表庫
    // 目前只顯示簡單的統計數據
    
    if (type === 'batting-stats') {
        createBattingChart(container, data);
    } else if (type === 'pitching-stats') {
        createPitchingChart(container, data);
    }
}

// 建立打擊統計圖表
function createBattingChart(container, data) {
    const chartHtml = `
        <div class="simple-chart">
            <h4>打擊統計</h4>
            <div class="stat-bars">
                <div class="stat-bar">
                    <span class="stat-name">打擊率</span>
                    <div class="bar">
                        <div class="fill" style="width: ${(data.avg || 0.250) * 400}px"></div>
                    </div>
                    <span class="stat-value">${(data.avg || 0.250).toFixed(3)}</span>
                </div>
                <div class="stat-bar">
                    <span class="stat-name">全壘打</span>
                    <div class="bar">
                        <div class="fill" style="width: ${(data.homeRuns || 0) * 2}px"></div>
                    </div>
                    <span class="stat-value">${data.homeRuns || 0}</span>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = chartHtml;
}

// 建立投球統計圖表
function createPitchingChart(container, data) {
    const chartHtml = `
        <div class="simple-chart">
            <h4>投球統計</h4>
            <div class="stat-bars">
                <div class="stat-bar">
                    <span class="stat-name">自責分率</span>
                    <div class="bar">
                        <div class="fill" style="width: ${(6 - (data.era || 4.00)) * 50}px"></div>
                    </div>
                    <span class="stat-value">${(data.era || 4.00).toFixed(2)}</span>
                </div>
                <div class="stat-bar">
                    <span class="stat-name">三振數</span>
                    <div class="bar">
                        <div class="fill" style="width: ${(data.strikeOuts || 0) / 2}px"></div>
                    </div>
                    <span class="stat-value">${data.strikeOuts || 0}</span>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = chartHtml;
}

// 初始化 AI 功能
function initializeAIFeatures() {
    const aiButtons = document.querySelectorAll('.ai-recommend-btn');
    
    aiButtons.forEach(button => {
        button.addEventListener('click', function() {
            const playerId = this.getAttribute('data-player-id');
            if (playerId) {
                loadAIRecommendations(playerId);
            }
        });
    });
}

// 載入 AI 推薦
function loadAIRecommendations(playerId) {
    const loadingHtml = '<div class="loading"><div class="spinner"></div></div>';
    const recommendationsContainer = document.getElementById('ai-recommendations');
    
    if (recommendationsContainer) {
        recommendationsContainer.innerHTML = loadingHtml;
        
        fetch(`/players/${playerId}/ai-recommendations/`)
            .then(response => response.text())
            .then(html => {
                recommendationsContainer.innerHTML = html;
            })
            .catch(error => {
                console.error('載入 AI 推薦錯誤:', error);
                recommendationsContainer.innerHTML = '<p class="text-danger">載入推薦時發生錯誤</p>';
            });
    }
}

// 表單驗證
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        const value = input.value.trim();
        
        if (!value) {
            showFieldError(input, '此欄位為必填');
            isValid = false;
        } else {
            clearFieldError(input);
        }
    });
    
    return isValid;
}

// 顯示欄位錯誤
function showFieldError(input, message) {
    clearFieldError(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.style.color = '#dc3545';
    errorDiv.style.fontSize = '0.8rem';
    errorDiv.style.marginTop = '0.25rem';
    errorDiv.textContent = message;
    
    input.parentElement.appendChild(errorDiv);
    input.style.borderColor = '#dc3545';
}

// 清除欄位錯誤
function clearFieldError(input) {
    const errorDiv = input.parentElement.querySelector('.field-error');
    if (errorDiv) {
        errorDiv.remove();
    }
    input.style.borderColor = '';
}

// 頁面載入動畫
function showPageLoading() {
    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'page-loading';
    loadingOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255,255,255,0.9);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    
    loadingOverlay.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingOverlay);
}

function hidePageLoading() {
    const loadingOverlay = document.getElementById('page-loading');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// 實用工具函數
const Utils = {
    // 格式化數字
    formatNumber: function(num) {
        return num.toLocaleString();
    },
    
    // 格式化打擊率
    formatAverage: function(avg) {
        return parseFloat(avg).toFixed(3);
    },
    
    // 格式化自責分率
    formatERA: function(era) {
        return parseFloat(era).toFixed(2);
    },
    
    // 複製到剪貼簿
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('已複製到剪貼簿', 'success');
        });
    },
    
    // 顯示通知
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem;
            border-radius: 5px;
            color: white;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        
        if (type === 'success') notification.style.background = '#28a745';
        else if (type === 'error') notification.style.background = '#dc3545';
        else if (type === 'warning') notification.style.background = '#ffc107';
        else notification.style.background = '#17a2b8';
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
};

// CSS 動畫
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .stat-bars {
        margin: 1rem 0;
    }
    
    .stat-bar {
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .stat-name {
        width: 100px;
        font-size: 0.9rem;
    }
    
    .bar {
        flex: 1;
        height: 20px;
        background: #e9ecef;
        border-radius: 10px;
        overflow: hidden;
        margin: 0 10px;
    }
    
    .fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea, #764ba2);
        transition: width 0.5s ease;
    }
    
    .stat-value {
        font-weight: bold;
        font-size: 0.9rem;
    }
`;
document.head.appendChild(style);

// 初始化主題切換
function initializeThemeToggle() {
    const toggleBtn = document.getElementById('theme-toggle');
    if (!toggleBtn) return;

    const iconSun = document.getElementById('theme-icon-sun');
    const iconMoon = document.getElementById('theme-icon-moon');

    function applyTheme(dark) {
        if (dark) {
            document.documentElement.classList.add('dark');
            iconSun && iconSun.classList.remove('hidden');
            iconMoon && iconMoon.classList.add('hidden');
        } else {
            document.documentElement.classList.remove('dark');
            iconSun && iconSun.classList.add('hidden');
            iconMoon && iconMoon.classList.remove('hidden');
        }
    }

    const stored = localStorage.getItem('theme');
    if (stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        applyTheme(true);
    }

    toggleBtn.addEventListener('click', () => {
        const isDark = document.documentElement.classList.toggle('dark');
        applyTheme(isDark);
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
}
