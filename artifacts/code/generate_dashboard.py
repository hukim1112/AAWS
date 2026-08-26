import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정 (없을 경우 기본 Sans-serif 및 Nanum/Malgun 처리)
fonts = [f.name for f in fm.fontManager.ttflist]
korean_fonts = ['NanumGothic', 'NanumBarunGothic', 'Malgun Gothic', 'AppleGothic', 'Noto Sans CJK KR']
selected_font = 'sans-serif'
for kf in korean_fonts:
    if kf in fonts:
        selected_font = kf
        break

plt.rcParams['font.family'] = selected_font
plt.rcParams['axes.unicode_minus'] = False

# 데이터 로드
json_path = 'artifacts/runs/scraper_20260827_041728_968d5f/danawa_03_bulk_detail_crawling_result.json'
with open(json_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

df = pd.DataFrame(raw_data)

# 브랜드 추출 함수
def extract_brand(name):
    first_word = name.split()[0]
    # 영문/한글 대소문자 정리
    return first_word.upper()

df['brand'] = df['product_name'].apply(extract_brand)
df['switch_type'] = df['switch_type'].fillna('일반/멤브레인/무접점')
df['connection_type'] = df['connection_type'].fillna('기타')
df['price'] = pd.to_numeric(df['price'], errors='coerce')
df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce').fillna(0).astype(int)

# 1. Excel 보고서 생성
excel_path = 'artifacts/danawa_keyboard_market_report.xlsx'
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='전체_데이터', index=False)
    
    # 브랜드별 통계
    brand_stats = df.groupby('brand').agg(
        상품수=('product_name', 'count'),
        평균가격=('price', 'mean'),
        최저가=('price', 'min'),
        최고가=('price', 'max'),
        총리뷰수=('review_count', 'sum')
    ).reset_index().sort_values(by='상품수', ascending=False)
    brand_stats.to_excel(writer, sheet_name='브랜드별_요약', index=False)
    
    # 연결방식별 통계
    conn_stats = df.groupby('connection_type').agg(
        상품수=('product_name', 'count'),
        평균가격=('price', 'mean'),
        총리뷰수=('review_count', 'sum')
    ).reset_index().sort_values(by='상품수', ascending=False)
    conn_stats.to_excel(writer, sheet_name='연결방식_요약', index=False)
    
    # 스위치별 통계
    switch_stats = df.groupby('switch_type').agg(
        상품수=('product_name', 'count'),
        평균가격=('price', 'mean'),
        총리뷰수=('review_count', 'sum')
    ).reset_index().sort_values(by='상품수', ascending=False)
    switch_stats.to_excel(writer, sheet_name='스위치별_요약', index=False)

print("Excel generated:", excel_path)

# 2. 고화질 정적 분석 차트 이미지 생성 (PNG)
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('다나와 키보드 시장 분석 인포그래픽', fontsize=18, fontweight='bold', y=0.98)

# 2-1. 주요 브랜드별 상품 수 (Top 8)
top_brands = df['brand'].value_counts().head(8)
axes[0, 0].bar(top_brands.index, top_brands.values, color='#4F46E5', alpha=0.85, edgecolor='black', linewidth=0.5)
axes[0, 0].set_title('Top 8 주요 브랜드 상품 수', fontsize=13, fontweight='bold')
axes[0, 0].set_ylabel('상품 수 (개)')
axes[0, 0].tick_params(axis='x', rotation=30)
for i, v in enumerate(top_brands.values):
    axes[0, 0].text(i, v + 0.5, str(v), ha='center', fontweight='bold', fontsize=10)

# 2-2. 연결 방식 점유율
conn_counts = df['connection_type'].value_counts()
colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']
axes[0, 1].pie(conn_counts.values, labels=conn_counts.index, autopct='%1.1f%%', 
               startangle=140, colors=colors[:len(conn_counts)],
               wedgeprops={'edgecolor': 'white', 'linewidth': 2})
axes[0, 1].set_title('연결 방식 점유율', fontsize=13, fontweight='bold')

# 2-3. 가격대별 분포 (히스토그램 & 구간)
price_bins = [0, 30000, 60000, 100000, 150000, 250000, 1000000]
bin_labels = ['~3만원', '3~6만원', '6~10만원', '10~15만원', '15~25만원', '25만원~']
df['price_tier'] = pd.cut(df['price'], bins=price_bins, labels=bin_labels, right=False)
tier_counts = df['price_tier'].value_counts()[bin_labels]

axes[1, 0].bar(tier_counts.index, tier_counts.values, color='#06B6D4', alpha=0.85, edgecolor='black', linewidth=0.5)
axes[1, 0].set_title('가격대별 상품 분포', fontsize=13, fontweight='bold')
axes[1, 0].set_ylabel('상품 수 (개)')
axes[1, 0].tick_params(axis='x', rotation=30)
for i, v in enumerate(tier_counts.values):
    axes[1, 0].text(i, v + 0.5, str(v), ha='center', fontweight='bold', fontsize=10)

# 2-4. 리뷰 수 상위 Top 8 인기 상품
top_reviews = df.sort_values(by='review_count', ascending=False).head(8)
short_names = [name[:18] + '...' if len(name) > 18 else name for name in top_reviews['product_name']]
axes[1, 1].barh(short_names[::-1], top_reviews['review_count'].values[::-1], color='#EC4899', alpha=0.85, edgecolor='black', linewidth=0.5)
axes[1, 1].set_title('최다 리뷰 인기 상품 Top 8', fontsize=13, fontweight='bold')
axes[1, 1].set_xlabel('리뷰 수 (건)')

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
png_path = 'artifacts/danawa_keyboard_market_analysis.png'
plt.savefig(png_path, dpi=200)
plt.close()
print("Chart PNG generated:", png_path)

# 3. 인터랙티브 반응형 HTML 대시보드 생성
# 데이터 JSON 변환
dashboard_data_json = df.to_json(orient='records', force_ascii=False)

html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>다나와 키보드 시장 분석 대시보드</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&display=swap');
        body {{
            font-family: 'Pretendard', sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
        }}
        .glass-card {{
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .custom-scrollbar::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        .custom-scrollbar::-webkit-scrollbar-thumb {{
            background: #475569;
            border-radius: 4px;
        }}
    </style>
</head>
<body class="min-h-screen p-4 md:p-8 custom-scrollbar">

    <!-- Header -->
    <div class="max-w-7xl mx-auto space-y-6">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-700/60 pb-6">
            <div>
                <div class="flex items-center gap-3">
                    <div class="p-2.5 bg-indigo-600/30 text-indigo-400 rounded-xl border border-indigo-500/30">
                        <i data-lucide="keyboard" class="w-7 h-7"></i>
                    </div>
                    <div>
                        <h1 class="text-2xl md:text-3xl font-extrabold text-white tracking-tight">다나와 키보드 시장 분석 대시보드</h1>
                        <p class="text-sm text-slate-400 mt-0.5">실시간 다나와 크롤링 데이터 기반 키보드 시장 트렌드 및 가격/스펙 심층 분석</p>
                    </div>
                </div>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-400 bg-slate-800/80 px-3.5 py-2 rounded-lg border border-slate-700">
                <i data-lucide="clock" class="w-4 h-4 text-indigo-400"></i>
                <span>데이터 수집 기준: 2026-08-27</span>
            </div>
        </div>

        <!-- KPI Summary Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <!-- Card 1 -->
            <div class="glass-card rounded-2xl p-5 relative overflow-hidden group hover:border-indigo-500/50 transition duration-300">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">분석 상품 수</p>
                        <h3 class="text-2xl md:text-3xl font-black text-white mt-1" id="kpi-total-items">{len(df):,} <span class="text-sm font-normal text-slate-400">개</span></h3>
                    </div>
                    <div class="p-2.5 bg-blue-500/20 text-blue-400 rounded-xl">
                        <i data-lucide="layers" class="w-5 h-5"></i>
                    </div>
                </div>
                <div class="mt-3 text-xs text-slate-400 flex items-center gap-1.5">
                    <span class="text-emerald-400 font-bold">100%</span> 크롤링 데이터 분석 완료
                </div>
            </div>

            <!-- Card 2 -->
            <div class="glass-card rounded-2xl p-5 relative overflow-hidden group hover:border-indigo-500/50 transition duration-300">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">평균 가격</p>
                        <h3 class="text-2xl md:text-3xl font-black text-white mt-1">{int(df['price'].mean()):,} <span class="text-sm font-normal text-slate-400">원</span></h3>
                    </div>
                    <div class="p-2.5 bg-emerald-500/20 text-emerald-400 rounded-xl">
                        <i data-lucide="badge-dollar-sign" class="w-5 h-5"></i>
                    </div>
                </div>
                <div class="mt-3 text-xs text-slate-400 flex items-center gap-1.5">
                    중앙값: <span class="text-slate-200 font-semibold">{int(df['price'].median()):,}원</span>
                </div>
            </div>

            <!-- Card 3 -->
            <div class="glass-card rounded-2xl p-5 relative overflow-hidden group hover:border-indigo-500/50 transition duration-300">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">최대 브랜드 점유</p>
                        <h3 class="text-2xl md:text-3xl font-black text-indigo-400 mt-1">{df['brand'].value_counts().index[0]} <span class="text-sm font-normal text-slate-400">({df['brand'].value_counts().values[0]}개)</span></h3>
                    </div>
                    <div class="p-2.5 bg-indigo-500/20 text-indigo-400 rounded-xl">
                        <i data-lucide="crown" class="w-5 h-5"></i>
                    </div>
                </div>
                <div class="mt-3 text-xs text-slate-400">
                    가성비/독거미 열풍 지속 주도
                </div>
            </div>

            <!-- Card 4 -->
            <div class="glass-card rounded-2xl p-5 relative overflow-hidden group hover:border-indigo-500/50 transition duration-300">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider">누적 사용자 리뷰</p>
                        <h3 class="text-2xl md:text-3xl font-black text-pink-400 mt-1">{df['review_count'].sum():,} <span class="text-sm font-normal text-slate-400">건</span></h3>
                    </div>
                    <div class="p-2.5 bg-pink-500/20 text-pink-400 rounded-xl">
                        <i data-lucide="message-square" class="w-5 h-5"></i>
                    </div>
                </div>
                <div class="mt-3 text-xs text-slate-400">
                    최고 리뷰: <span class="text-pink-300 font-semibold">{df.sort_values(by='review_count', ascending=False).iloc[0]['review_count']}건</span> ({df.sort_values(by='review_count', ascending=False).iloc[0]['brand']})
                </div>
            </div>
        </div>

        <!-- Charts Section Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Chart 1: Brand Distribution -->
            <div class="glass-card rounded-2xl p-5">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-base font-bold text-white flex items-center gap-2">
                        <i data-lucide="bar-chart-2" class="w-4 h-4 text-indigo-400"></i>
                        주요 브랜드별 등록 상품 수 & 평균가
                    </h2>
                </div>
                <div class="h-64">
                    <canvas id="brandChart"></canvas>
                </div>
            </div>

            <!-- Chart 2: Connection Type -->
            <div class="glass-card rounded-2xl p-5">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-base font-bold text-white flex items-center gap-2">
                        <i data-lucide="pie-chart" class="w-4 h-4 text-emerald-400"></i>
                        키보드 연결 방식 점유율
                    </h2>
                </div>
                <div class="h-64 flex items-center justify-center">
                    <canvas id="connectionChart"></canvas>
                </div>
            </div>

            <!-- Chart 3: Price Tiers -->
            <div class="glass-card rounded-2xl p-5">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-base font-bold text-white flex items-center gap-2">
                        <i data-lucide="trending-up" class="w-4 h-4 text-cyan-400"></i>
                        가격대 구간별 분포 현황
                    </h2>
                </div>
                <div class="h-64">
                    <canvas id="priceTierChart"></canvas>
                </div>
            </div>

            <!-- Chart 4: Switch Types -->
            <div class="glass-card rounded-2xl p-5">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-base font-bold text-white flex items-center gap-2">
                        <i data-lucide="cpu" class="w-4 h-4 text-purple-400"></i>
                        주요 스위치 / 축 타입 분포
                    </h2>
                </div>
                <div class="h-64">
                    <canvas id="switchChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Interactive Data Table & Filter -->
        <div class="glass-card rounded-2xl p-5">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
                <div>
                    <h2 class="text-lg font-bold text-white flex items-center gap-2">
                        <i data-lucide="table" class="w-5 h-5 text-indigo-400"></i>
                        상품별 상세 스펙 및 가격 검색기
                    </h2>
                    <p class="text-xs text-slate-400 mt-0.5">원하는 브랜드, 스위치 또는 상품명을 입력해 필터링해보세요.</p>
                </div>
                <div class="flex flex-wrap items-center gap-3 w-full md:w-auto">
                    <input type="text" id="searchInput" placeholder="상품명/브랜드/스위치 검색..." 
                           class="bg-slate-900/90 border border-slate-700 text-sm rounded-xl px-4 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-full md:w-64">
                    <select id="connFilter" class="bg-slate-900/90 border border-slate-700 text-sm rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500">
                        <option value="ALL">연결방식 전체</option>
                        <option value="유선+무선">유선+무선</option>
                        <option value="유선">유선</option>
                        <option value="무선">무선</option>
                    </select>
                </div>
            </div>

            <!-- Table Container -->
            <div class="overflow-x-auto custom-scrollbar max-h-96 border border-slate-700/60 rounded-xl">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="text-xs uppercase bg-slate-800/80 text-slate-400 sticky top-0 backdrop-blur z-10">
                        <tr>
                            <th scope="col" class="px-4 py-3">브랜드</th>
                            <th scope="col" class="px-4 py-3">상품명</th>
                            <th scope="col" class="px-4 py-3">스위치/축</th>
                            <th scope="col" class="px-4 py-3">연결방식</th>
                            <th scope="col" class="px-4 py-3 text-right">가격</th>
                            <th scope="col" class="px-4 py-3 text-right">리뷰수</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody" class="divide-y divide-slate-800">
                        <!-- Rows dynamically rendered -->
                    </tbody>
                </table>
            </div>
            <div class="mt-3 flex justify-between items-center text-xs text-slate-400">
                <span id="filteredCount">표시 중인 상품: 0개</span>
                <span>정렬: 인기/추천순</span>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center text-xs text-slate-500 pb-4">
            <p>다나와(Danawa) 키보드 카테고리 데이터 심층 분석 | Automated Multi-Agent BI Dashboard</p>
        </div>
    </div>

    <!-- Script Logic -->
    <script>
        const rawData = {dashboard_data_json};

        // Lucide Icons init
        lucide.createIcons();

        // 1. Chart: Brands
        const brandMap = {{}};
        rawData.forEach(item => {{
            const b = item.brand || '기타';
            if (!brandMap[b]) brandMap[b] = {{ count: 0, totalPrice: 0 }};
            brandMap[b].count++;
            brandMap[b].totalPrice += item.price || 0;
        }});

        const sortedBrands = Object.keys(brandMap)
            .map(k => ({{ brand: k, count: brandMap[k].count, avgPrice: Math.round(brandMap[k].totalPrice / brandMap[k].count) }}))
            .sort((a, b) => b.count - a.count)
            .slice(0, 8);

        new Chart(document.getElementById('brandChart'), {{
            type: 'bar',
            data: {{
                labels: sortedBrands.map(d => d.brand),
                datasets: [{{
                    label: '상품 수 (개)',
                    data: sortedBrands.map(d => d.count),
                    backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    borderColor: '#6366f1',
                    borderWidth: 1,
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
                }}
            }}
        }});

        // 2. Chart: Connection
        const connMap = {{}};
        rawData.forEach(item => {{
            const c = item.connection_type || '기타';
            connMap[c] = (connMap[c] || 0) + 1;
        }});

        new Chart(document.getElementById('connectionChart'), {{
            type: 'doughnut',
            data: {{
                labels: Object.keys(connMap),
                datasets: [{{
                    data: Object.values(connMap),
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: '#cbd5e1', boxWidth: 12 }} }}
                }}
            }}
        }});

        // 3. Chart: Price Tiers
        const tiers = {{ '~3만원': 0, '3~6만원': 0, '6~10만원': 0, '10~15만원': 0, '15~25만원': 0, '25만원~': 0 }};
        rawData.forEach(item => {{
            const p = item.price || 0;
            if (p < 30000) tiers['~3만원']++;
            else if (p < 60000) tiers['3~6만원']++;
            else if (p < 100000) tiers['6~10만원']++;
            else if (p < 150000) tiers['10~15만원']++;
            else if (p < 250000) tiers['15~25만원']++;
            else tiers['25만원~']++;
        }});

        new Chart(document.getElementById('priceTierChart'), {{
            type: 'bar',
            data: {{
                labels: Object.keys(tiers),
                datasets: [{{
                    label: '상품 수',
                    data: Object.values(tiers),
                    backgroundColor: 'rgba(6, 182, 212, 0.8)',
                    borderColor: '#06b6d4',
                    borderWidth: 1,
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
                }}
            }}
        }});

        // 4. Chart: Switches
        const switchMap = {{}};
        rawData.forEach(item => {{
            const s = item.switch_type || '일반/기타';
            switchMap[s] = (switchMap[s] || 0) + 1;
        }});
        const sortedSwitches = Object.keys(switchMap)
            .map(k => ({{ type: k, count: switchMap[k] }}))
            .sort((a, b) => b.count - a.count)
            .slice(0, 6);

        new Chart(document.getElementById('switchChart'), {{
            type: 'bar',
            data: {{
                labels: sortedSwitches.map(s => s.type),
                datasets: [{{
                    label: '상품 수',
                    data: sortedSwitches.map(s => s.count),
                    backgroundColor: 'rgba(168, 85, 247, 0.8)',
                    borderColor: '#a855f7',
                    borderWidth: 1,
                    borderRadius: 6
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
                    y: {{ grid: {{ display: false }}, ticks: {{ color: '#cbd5e1' }} }}
                }}
            }}
        }});

        // Table Render & Filter
        const searchInput = document.getElementById('searchInput');
        const connFilter = document.getElementById('connFilter');
        const tableBody = document.getElementById('tableBody');
        const filteredCount = document.getElementById('filteredCount');

        function renderTable() {{
            const query = searchInput.value.toLowerCase().trim();
            const conn = connFilter.value;

            const filtered = rawData.filter(item => {{
                const matchQuery = !query || 
                    (item.product_name && item.product_name.toLowerCase().includes(query)) ||
                    (item.brand && item.brand.toLowerCase().includes(query)) ||
                    (item.switch_type && item.switch_type.toLowerCase().includes(query));
                const matchConn = conn === 'ALL' || item.connection_type === conn;
                return matchQuery && matchConn;
            }});

            filteredCount.innerText = `표시 중인 상품: ${{filtered.length}}개`;

            tableBody.innerHTML = filtered.map(item => `
                <tr class="hover:bg-slate-800/50 transition">
                    <td class="px-4 py-3 font-semibold text-indigo-300">${{item.brand}}</td>
                    <td class="px-4 py-3 text-slate-200 font-medium">${{item.product_name}}</td>
                    <td class="px-4 py-3 text-slate-400"><span class="px-2 py-0.5 rounded text-xs bg-slate-800 border border-slate-700">${{item.switch_type}}</span></td>
                    <td class="px-4 py-3">
                        <span class="px-2 py-0.5 rounded text-xs ${{
                            item.connection_type === '유선+무선' ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' :
                            item.connection_type === '무선' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                            'bg-slate-700/40 text-slate-300 border border-slate-600/30'
                        }}">${{item.connection_type}}</span>
                    </td>
                    <td class="px-4 py-3 text-right font-bold text-white">${{(item.price || 0).toLocaleString()}}원</td>
                    <td class="px-4 py-3 text-right text-pink-400 font-semibold">${{(item.review_count || 0).toLocaleString()}}</td>
                </tr>
            `).join('');
        }}

        searchInput.addEventListener('input', renderTable);
        connFilter.addEventListener('change', renderTable);
        renderTable();
    </script>
</body>
</html>
"""

html_path = 'artifacts/danawa_keyboard_market_dashboard.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
print("HTML Dashboard generated:", html_path)

# 4. 종합 요약 마크다운 생성
summary_md = f"""# ⌨️ 다나와 키보드 시장 분석 보고서 (2026년 8월)

## 1. 데이터 개요
- **총 수집 상품 수**: {len(df)}개
- **평균 가격**: {int(df['price'].mean()):,}원 (중앙값: {int(df['price'].median()):,}원)
- **최고가 / 최저가**: {int(df['price'].max()):,}원 / {int(df['price'].min()):,}원
- **총 리뷰 수**: {df['review_count'].sum():,}건

---

## 2. 주요 시장 트렌드 & 인사이트
1. **AULA(독거미) 열풍의 지속**:
   - 독거미 시리즈(F87, F108 등)가 가성비 기계식 키보드 시장을 장악하며 최상위권 점유율과 높은 리뷰 수를 기록하고 있습니다.
   - 특히 '저소음 바다축', '저소음 피치축' 등 저소음 리니어 스위치 모델의 인기가 압도적입니다.

2. **유선+무선(3-Mode) 연결 방식의 대중화**:
   - 6~10만원대 중급형 기계식 키보드 대부분이 블루투스, 2.4GHz 동글, 유선을 모두 지원하는 3-Mode 유무선 규격을 기본 채택하고 있습니다.

3. **초고가 플래그십 게이밍 vs 보급형 가성비 양극화**:
   - 커세어(CORSAIR), 레이저(Razer) 등 20~30만원대 자석축/무접점 플래그십 라인업과 앱코/AULA 등 3~8만원대 가성비 라인업으로 시장이 뚜렷하게 양분되어 있습니다.

---

## 3. 결과 파일 목록
- **인터랙티브 대시보드**: `artifacts/danawa_keyboard_market_dashboard.html`
- **시각화 인포그래픽**: `artifacts/danawa_keyboard_market_analysis.png`
- **Excel 상세 보고서**: `artifacts/danawa_keyboard_market_report.xlsx`
"""

summary_path = 'artifacts/danawa_keyboard_market_summary.md'
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write(summary_md)
print("Summary MD generated:", summary_path)
