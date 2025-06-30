import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib

# ───────────── 한글 폰트 & 스타일 ─────────────
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid")

st.markdown("---")
st.markdown("## 📊 정책별 샘플 그래프 (가상 데이터)")

col1, col2, col3 = st.columns(3)

# ───────────── 1) 농가별 생산량 (Barplot) ─────────────
with col1:
    st.markdown("### ✅ 농가별 생산량")
    farmers = [f'농가 {c}' for c in ['A','B','C','D','E','F']]
    np.random.seed(42)
    prod = np.random.randint(80, 150, size=6)
    fig, ax = plt.subplots(figsize=(4,3))
    sns.barplot(x=farmers, y=prod, palette="pastel", ax=ax)
    ax.set_ylabel("연간 생산량 (톤)", fontsize=10)
    ax.set_title("농가별 연간 생산량 비교", fontsize=12)
    for i, v in enumerate(prod):
        ax.text(i, v+2, f"{v}t", ha='center', fontsize=8)
    st.pyplot(fig)

# ───────────── 2) 권역별 지표 분포 (Boxplot) ─────────────
with col2:
    st.markdown("### ✅ 권역별 지표 분포")
    data = [np.random.normal(100+10*i, 10+2*i, 60) for i in range(4)]
    fig, ax = plt.subplots(figsize=(4,3))
    labels = [f'권역 {c}' for c in ['A','B','C','D']]
    ax.boxplot(data, labels=labels, patch_artist=True,
               boxprops=dict(facecolor='#90be6d'),
               medianprops=dict(color='white', linewidth=2))
    ax.set_title("권역별 농가 지표 분포", fontsize=12)
    ax.set_ylabel("지표값", fontsize=10)
    st.pyplot(fig)

# ───────────── 3) 월별 계절성 추이 (Lineplot) ─────────────
with col3:
    st.markdown("### ✅ 월별 계절성 추이")
    months = np.arange(1,13)
    seasonal = 50 + 15 * np.sin(np.linspace(0, 2*np.pi, 12)) + np.random.normal(0,2,12)
    fig, ax = plt.subplots(figsize=(4,3))
    sns.lineplot(x=months, y=seasonal, marker='o', linewidth=2, color="#0077b6", ax=ax)
    ax.set_title("월별 생산량 계절성 추이", fontsize=12)
    ax.set_xlabel("월", fontsize=10)
    ax.set_ylabel("생산지수", fontsize=10)
    ax.set_xticks(months)
    for x, y in zip(months, seasonal):
        ax.text(x, y+0.8, f"{y:.1f}", ha='center', fontsize=7)
    st.pyplot(fig)

# ───────────── 4) 탄소배출 구성비 (Pie) ─────────────
with col1:
    st.markdown("### ✅ 탄소배출 구성비")
    labels = ['운송', '사료', '에너지', '시설', '기타']
    sizes = [35, 25, 20, 10, 10]
    fig, ax = plt.subplots(figsize=(4,3))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%', startangle=90,
        colors=sns.color_palette("pastel"),
        wedgeprops=dict(width=0.5, edgecolor='w'))
    ax.set_title("탄소배출 카테고리별 비중 (%)", fontsize=12)
    st.pyplot(fig)

# ───────────── 5) 축산업 혁신 지표 (Heatmap) ─────────────
with col2:
    st.markdown("### ✅ 축산업 혁신 지표")
    fig, ax = plt.subplots(figsize=(4,3))
    corr_matrix = np.round(np.random.uniform(0.2, 0.95, size=(6,6)), 2)
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="YlGnBu",
                linewidths=0.5, linecolor='gray',
                cbar_kws={'label': '상관계수'}, ax=ax)
    ax.set_title("혁신요소 간 상관관계", fontsize=12)
    st.pyplot(fig)

# ───────────── 6) 시장 동향 (Scatter) ─────────────
with col3:
    st.markdown("### ✅ 시장 동향")
    np.random.seed(123)
    price = np.random.uniform(2000, 8000, 100)
    vol = 40 + 0.015 * price + np.random.normal(0, 5, 100)
    fig, ax = plt.subplots(figsize=(4,3))
    sns.scatterplot(x=price, y=vol, color="#023047", s=40, edgecolor='w', ax=ax)
    ax.set_title("가격-거래량 상관관계", fontsize=12)
    ax.set_xlabel("가격 (원/kg)", fontsize=10)
    ax.set_ylabel("거래량 (톤)", fontsize=10)
    st.pyplot(fig)
