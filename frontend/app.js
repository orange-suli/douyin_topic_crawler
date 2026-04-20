// Global Configuration
const API_BASE_URL = 'http://localhost:8000';

// Global Chart Instances
let chartInstances = [];

// ── Utility: 格式化大数字（万/亿单位）──────────────────────────
function fmtNum(n) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    if (n >= 1e8) return (n / 1e8).toFixed(1) + '亿';
    if (n >= 1e4) return (n / 1e4).toFixed(1) + 'w';
    return n.toLocaleString();
}

// DOM Elements
const errorBanner = document.getElementById('error-banner');

// Utility: Show Error
function showError() {
    errorBanner.classList.remove('hidden');
}

// Utility: Render "No Data" placeholder
function renderNoData(containerId) {
    const container = document.getElementById(containerId);
    let placeholder = container.querySelector('.no-data-placeholder');
    if (!placeholder) {
        placeholder = document.createElement('div');
        placeholder.className = 'no-data-placeholder';
        placeholder.innerText = '暂无数据';
        container.appendChild(placeholder);
    }
}

// Utility: Remove "No Data" placeholder
function removeNoData(containerId) {
    const container = document.getElementById(containerId);
    const placeholder = container.querySelector('.no-data-placeholder');
    if (placeholder) {
        placeholder.remove();
    }
}

// 1. Render Interaction Bar Chart
function renderBarChart(data) {
    const containerId = 'bar-chart';
    if (!data || Object.keys(data).length === 0 || Object.values(data).every(v => v === 0)) {
        renderNoData(containerId);
        return;
    }
    removeNoData(containerId);

    const chartDom = document.getElementById(containerId);
    const myChart = echarts.init(chartDom, 'dark');
    chartInstances.push(myChart);

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: [
            {
                type: 'category',
                data: ['点赞', '评论', '分享', '收藏'],
                axisTick: { alignWithLabel: true },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.3)' } }
            }
        ],
        yAxis: [
            {
                type: 'value',
                splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)', type: 'dashed' } }
            }
        ],
        series: [
            {
                name: '互动量',
                type: 'bar',
                barWidth: '50%',
                data: [
                    data.total_digg || 0,
                    data.total_comment || 0,
                    data.total_share || 0,
                    data.total_collect || 0
                ],
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#00f2fe' },
                        { offset: 1, color: '#4facfe' }
                    ]),
                    borderRadius: [4, 4, 0, 0]
                }
            }
        ]
    };

    myChart.setOption(option);
}

// 2. Render Tag Word Cloud
function renderWordCloud(tagCloudData) {
    const containerId = 'wordcloud-chart';
    if (!tagCloudData || Object.keys(tagCloudData).length === 0) {
        renderNoData(containerId);
        return;
    }
    removeNoData(containerId);
    
    // Transform dict to array format expected by wordcloud
    const dataList = Object.entries(tagCloudData).map(([name, value]) => ({
        name: name,
        value: value
    }));

    const chartDom = document.getElementById(containerId);
    const myChart = echarts.init(chartDom, 'dark');
    chartInstances.push(myChart);

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            show: true
        },
        series: [{
            type: 'wordCloud',
            shape: 'circle',
            keepAspect: false,
            left: 'center',
            top: 'center',
            width: '100%',
            height: '100%',
            sizeRange: [12, 60],
            rotationRange: [-90, 90],
            rotationStep: 45,
            gridSize: 8,
            drawOutOfBound: false,
            layoutAnimation: true,
            textStyle: {
                color: function () {
                    // Random color generation for dynamic look
                    const colors = ['#00f2fe', '#4facfe', '#fa709a', '#fee140', '#43e97b', '#b3ffab'];
                    return colors[Math.floor(Math.random() * colors.length)];
                }
            },
            data: dataList
        }]
    };

    myChart.setOption(option);
}

// 3. Render Scatter Plot (Followers vs Interaction Rate)
function renderScatterChart(scatterData) {
    const containerId = 'scatter-chart';
    if (!scatterData || scatterData.length === 0) {
        renderNoData(containerId);
        return;
    }
    removeNoData(containerId);

    const chartDom = document.getElementById(containerId);
    const myChart = echarts.init(chartDom, 'dark');
    chartInstances.push(myChart);
    
    // x: follower count, y: interaction rate, size/color can represent total interaction
    const formatData = scatterData.map(item => {
        return [
            item.follower_count,
            item.interaction_rate * 100, // convert back to percentage visually if needed, though raw is fine
            item.total_interaction,
            item.nickname,
            item.aweme_id
        ];
    });

    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                const author = params.data[3];
                const followers = params.data[0].toLocaleString();
                const rate = params.data[1].toFixed(2) + '%';
                const interactions = params.data[2].toLocaleString();
                return `
                    <div style="padding: 4px; border-radius: 4px;">
                        <span style="font-weight: 600; font-size: 14px; color: #fff;">${author}</span><br/>
                        粉丝数: <span style="color: #00f2fe">${followers}</span><br/>
                        互动率: <span style="color: #fa709a">${rate}</span><br/>
                        总互动量: <span style="color: #fee140">${interactions}</span>
                    </div>
                `;
            },
            backgroundColor: 'rgba(25, 30, 50, 0.9)',
            borderColor: 'rgba(255,255,255,0.2)',
            textStyle: { color: '#fff' }
        },
        xAxis: {
            type: 'log',
            name: '粉丝数 (对数轴)',
            nameLocation: 'middle',
            nameGap: 30,
            splitLine: { show: false },
            axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.3)' } }
        },
        yAxis: {
            type: 'value',
            name: '互动率 (%)',
            splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)', type: 'dashed' } }
        },
        series: [
            {
                type: 'scatter',
                data: formatData,
                symbolSize: function (data) {
                    // scale symbol size based on total interaction gently
                    let s = Math.sqrt(data[2]) / 10;
                    return Math.max(10, Math.min(s, 60)); 
                },
                itemStyle: {
                    color: new echarts.graphic.RadialGradient(0.4, 0.3, 1, [
                        { offset: 0, color: 'rgba(0, 242, 254, 0.8)' },
                        { offset: 1, color: 'rgba(79, 172, 254, 0.4)' }
                    ]),
                    borderColor: 'rgba(0, 242, 254, 1)',
                    borderWidth: 1
                }
            }
        ]
    };

    myChart.setOption(option);
}

// Fetch Data & Initialize
async function fetchAndRenderAll() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const keyword = urlParams.get('keyword');
        const fetchUrl = keyword ? `${API_BASE_URL}/api/stats?keyword=${encodeURIComponent(keyword)}` : `${API_BASE_URL}/api/stats`;
        const res = await fetch(fetchUrl);
        
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        const responseData = await res.json();
        
        if (responseData.code === 200 && responseData.data) {
            const stats = responseData.data;
            renderBarChart(stats.interaction_bar);
            renderWordCloud(stats.tag_cloud);
            renderScatterChart(stats.scatter_data);
        } else {
            throw new Error('Invalid backend response format');
        }
    } catch (e) {
        console.error('Failed to fetch stats:', e);
        showError();
        // Fallback layout just in case they haven't rendered
        renderNoData('bar-chart');
        renderNoData('wordcloud-chart');
        renderNoData('scatter-chart');
    }
    // 始终同步刷新详情列表（无论图表是否成功）
    await fetchAndRenderDetailList();
}

// ── 4. Render Video Detail List ────────────────────────────────
function renderDetailList(videos) {
    const listEl    = document.getElementById('video-list');
    const emptyEl   = document.getElementById('detail-empty');
    const countEl   = document.getElementById('detail-count');

    listEl.innerHTML = '';

    if (!videos || videos.length === 0) {
        emptyEl.classList.remove('hidden');
        countEl.classList.add('hidden');
        return;
    }

    emptyEl.classList.add('hidden');
    countEl.textContent = `共 ${videos.length} 条`;
    countEl.classList.remove('hidden');

    videos.forEach(v => {
        // Tags
        const tagsArr = Array.isArray(v.tags) ? v.tags : [];
        const tagHtml = tagsArr.length
            ? tagsArr.map(t => `<span class="tag-pill">#${t}</span>`).join('')
            : '<span style="color:var(--text-secondary);font-size:0.75rem">无标签</span>';

        // Video URL (guaranteed non-empty by API)
        const videoUrl = v.video_url || `https://www.douyin.com/video/${v.aweme_id}`;

        // Title – 用 <a> 包裹，双重跳转入口
        const titleText = v.title || '（无标题）';
        const titleHtml = `
            <a class="video-title-link"
               href="${videoUrl}"
               target="_blank"
               rel="noopener noreferrer"
               title="点击前往抖音观看: ${titleText.replace(/"/g, '&quot;')}">
                ${titleText}
                <span class="link-icon">↗</span>
            </a>`;

        // Stats row
        const statsHtml = `
            <div class="video-stats">
                <span class="stat-chip" title="点赞">
                    <span class="stat-icon">❤️</span>
                    <span class="stat-val">${fmtNum(v.digg_count)}</span>
                </span>
                <span class="stat-chip" title="评论">
                    <span class="stat-icon">💬</span>
                    <span class="stat-val">${fmtNum(v.comment_count)}</span>
                </span>
                <span class="stat-chip" title="转发">
                    <span class="stat-icon">🔁</span>
                    <span class="stat-val">${fmtNum(v.share_count)}</span>
                </span>
                <span class="stat-chip" title="收藏">
                    <span class="stat-icon">⭐</span>
                    <span class="stat-val">${fmtNum(v.collect_count)}</span>
                </span>
                <span class="stat-chip" title="播放">
                    <span class="stat-icon">▶️</span>
                    <span class="stat-val">${fmtNum(v.play_count)}</span>
                </span>
            </div>`;

        // Follower count
        const followerText = v.follower_count > 0
            ? `粉丝 ${fmtNum(v.follower_count)}`
            : '粉丝数未知';

        const itemHtml = `
            <div class="video-item" role="listitem">
                <div class="video-main">
                    ${titleHtml}
                    <div class="video-tags">${tagHtml}</div>
                    ${statsHtml}
                </div>
                <div class="video-meta">
                    <span class="author-name">@${v.author_nickname || '未知博主'}</span>
                    <span class="follower-chip">⭐ ${followerText}</span>
                    <a class="watch-btn"
                       href="${videoUrl}"
                       target="_blank"
                       rel="noopener noreferrer">
                        🔗 去观看
                    </a>
                </div>
            </div>`;

        listEl.insertAdjacentHTML('beforeend', itemHtml);
    });
}

async function fetchAndRenderDetailList() {
    const skeletonEl = document.getElementById('detail-skeleton');
    const listEl     = document.getElementById('video-list');
    const emptyEl    = document.getElementById('detail-empty');

    // Show skeleton, hide other states
    skeletonEl.classList.remove('hidden');
    emptyEl.classList.add('hidden');
    listEl.innerHTML = '';

    try {
        const urlParams = new URLSearchParams(window.location.search);
        const keyword = urlParams.get('keyword');
        const params = new URLSearchParams({ skip: 0, limit: 100 });
        if (keyword) params.append('keyword', keyword);

        const res = await fetch(`${API_BASE_URL}/api/videos/detailed?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();

        skeletonEl.classList.add('hidden');

        if (json.code === 200) {
            renderDetailList(json.data);
        } else {
            throw new Error(json.message || '接口返回异常');
        }
    } catch (e) {
        console.error('[详情列表] 加载失败:', e);
        skeletonEl.classList.add('hidden');
        emptyEl.querySelector('p').textContent = '详情数据加载失败，请检查后端服务状态';
        emptyEl.classList.remove('hidden');
    }
}

// Setup Crawl Control Panel
function setupCrawlButton() {
    const btn = document.getElementById('crawl-btn');
    const keywordInput = document.getElementById('crawl-keyword');
    const limitInput = document.getElementById('crawl-limit');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    const errorDiv = document.getElementById('crawl-error');

    // Initialize inputs from URL if present
    const urlParams = new URLSearchParams(window.location.search);
    if(urlParams.get('keyword')) {
        keywordInput.value = urlParams.get('keyword');
    }

    btn.addEventListener('click', async () => {
        const keyword = keywordInput.value.trim();
        const limit = parseInt(limitInput.value.trim()) || 10;

        if (!keyword) {
            errorDiv.innerText = '请输入有效的搜索关键词';
            errorDiv.classList.remove('hidden');
            return;
        }

        // Set Loading State
        errorDiv.classList.add('hidden');
        btn.disabled = true;
        btnText.classList.add('hidden');
        btnLoader.classList.remove('hidden');

        try {
            const res = await fetch(`${API_BASE_URL}/api/crawl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword, limit })
            });
            const responseData = await res.json();
            
            if (res.ok && responseData.code === 200) {
                // Update URL parameter without reloading page
                const newUrl = new URL(window.location);
                newUrl.searchParams.set('keyword', keyword);
                window.history.pushState({}, '', newUrl);

                // Fetch new data (charts + detail list)
                await fetchAndRenderAll();
            } else {
                throw new Error(responseData.message || responseData.detail || '抓取接口返回失败');
            }
        } catch (e) {
            console.error('Crawl failed:', e);
            errorDiv.innerText = '抓取异常: ' + e.message;
            errorDiv.classList.remove('hidden');
        } finally {
            // Remove Loading State
            btn.disabled = false;
            btnText.classList.remove('hidden');
            btnLoader.classList.add('hidden');
        }
    });
}

// Resize Charts on Window Resize
window.addEventListener('resize', () => {
    chartInstances.forEach(chart => {
        if(chart) chart.resize();
    });
});

// Bootstrap
document.addEventListener('DOMContentLoaded', () => {
    setupCrawlButton();
    fetchAndRenderAll();        // charts
    fetchAndRenderDetailList(); // detail list (独立请求，不依赖图表数据)
});
