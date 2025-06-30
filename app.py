import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

# ───────────── 글로벌 설정 ─────────────
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 6
sns.set_style("whitegrid")
np.random.seed(123)

# ───────────── 1) Seasonality Data ─────────────
months = np.tile(np.arange(1, 13), 50)
season_shipments = []
for m in range(1, 13):
    base = 100 + 30 * np.sin(2 * np.pi * m / 12)
    vals = base + np.random.normal(0, 5, 50)
    for v in vals:
        season_shipments.append({"Month": m, "Shipment": v})
df_season = pd.DataFrame(season_shipments)

# ───────────── 2) Farming Revenue ─────────────
farms = [f"Farm {chr(65+i)}" for i in range(10)]
farm_revenues = []
for farm in farms:
    for i in range(50):
        val = np.random.normal(50000, 5000) + np.random.uniform(-5000, 5000)
        farm_revenues.append({"Farm": farm, "Revenue": val})
df_farm = pd.DataFrame(farm_revenues)

# ───────────── 3) Innovation Heatmap ─────────────
df_heat = pd.DataFrame(
    np.round(np.random.rand(20, 20) * 100, 1),
    columns=[f"V{i+1}" for i in range(20)],
    index=[f"S{i+1}" for i in range(20)]
)

# ───────────── 4) Regional Production ─────────────
regions = ["Region A", "Region B", "Region C"]
region_production = []
for region in regions:
    for i in range(70):
        if region == "Region A":
            val = np.random.normal(150, 20)
        elif region == "Region B":
            val = np.random.normal(200, 30)
        else:
            val = np.random.normal(100, 15)
        region_production.append({"Region": region, "Production": val})
df_region = pd.DataFrame(region_production)

# ───────────── 5) Carbon Pie ─────────────
df_carbon = pd.DataFrame({
    "Category": ["Transport", "Feed", "Processing", "Waste", "Others"],
    "Ratio": [0.4, 0.25, 0.15, 0.1, 0.1]
})

# ───────────── 6) Market Scatter ─────────────
prices = np.random.uniform(1000, 20000, 200)
volumes = 100 + 0.02 * prices + np.random.normal(0, 10, 200)
df_market = pd.DataFrame({"Price": prices, "Volume": volumes})

# ───────────── Streamlit ─────────────
st.markdown("---")
st.markdown("### 📊 Final Seaborn Graphs (3 per row, same heights, small fonts)")

# ───────────── 첫 번째 줄 ─────────────
row1 = st.columns(3, gap="large")

with row1[0]:
    st.markdown("#### ✅ Seasonality")
    fig1, ax1 = plt.subplots(figsize=(4, 2.5))
    sns.lineplot(data=df_season, x="Month", y="Shipment", ci="sd", marker='o',
                 linewidth=0.8, markersize=2, ax=ax1,
                 palette=sns.color_palette("Paired"))
    ax1.set_title("Monthly Shipment", fontsize=6)
    ax1.set_xlabel("Month", fontsize=6)
    ax1.set_ylabel("Shipment", fontsize=6)
    ax1.tick_params(axis='both', labelsize=6)
    st.pyplot(fig1)

with row1[1]:
    st.markdown("#### ✅ Farming Revenue")
    fig2, ax2 = plt.subplots(figsize=(6, 3))  # 높이 키움
    sns.boxplot(data=df_farm, x="Farm", y="Revenue",
                palette="Paired", ax=ax2)
    sns.stripplot(data=df_farm, x="Farm", y="Revenue",
                  color=".3", size=1.5, jitter=True, ax=ax2)
    ax2.set_title("Revenue by Farm (10)", fontsize=6)
    ax2.set_xlabel("", fontsize=6)
    ax2.set_ylabel("Revenue ($)", fontsize=6)
    ax2.tick_params(axis='x', rotation=30, labelsize=6)
    ax2.tick_params(axis='y', labelsize=6)
    st.pyplot(fig2)

with row1[2]:
    st.markdown("#### ✅ Innovation Heatmap")
    fig3, ax3 = plt.subplots(figsize=(4, 2.5))
    sns.heatmap(df_heat, annot=True, fmt=".1f", cmap="coolwarm",
                cbar=False, annot_kws={"size": 4}, ax=ax3)
    ax3.set_title("Innovation Matrix", fontsize=6)
    ax3.tick_params(axis='both', labelsize=6)
    st.pyplot(fig3)

# ───────────── 두 번째 줄 ─────────────
row2 = st.columns(3, gap="large")

with row2[0]:
    st.markdown("#### ✅ Regional Production")
    fig4, ax4 = plt.subplots(figsize=(4, 2.5))
    sns.boxplot(data=df_region, x="Region", y="Production",
                palette="Paired", ax=ax4)
    sns.stripplot(data=df_region, x="Region", y="Production",
                  color=".3", size=1.5, jitter=True, ax=ax4)
    ax4.set_title("Production by Region", fontsize=6)
    ax4.set_xlabel("", fontsize=6)
    ax4.set_ylabel("Production", fontsize=6)
    ax4.tick_params(axis='both', labelsize=6)
    st.pyplot(fig4)

with row2[1]:
    st.markdown("#### ✅ Carbon Emission (Donut)")
    fig5, ax5 = plt.subplots(figsize=(2.5, 2))  # 더 작게
    colors = sns.color_palette("Paired")
    wedges, texts, autotexts = ax5.pie(df_carbon["Ratio"],
                                       labels=df_carbon["Category"],
                                       colors=colors[:5],
                                       autopct='%1.1f%%',
                                       textprops={'fontsize': 4},
                                       wedgeprops=dict(width=0.35))  # 도넛형
    ax5.set_title("Carbon Emission Breakdown", fontsize=6)
    st.pyplot(fig5)

with row2[2]:
    st.markdown("#### ✅ Market Trend")
    fig6, ax6 = plt.subplots(figsize=(4, 2.5))
    sns.scatterplot(data=df_market, x="Price", y="Volume",
                    s=8, color=sns.color_palette("Paired")[0], ax=ax6)
    sns.regplot(data=df_market, x="Price", y="Volume",
                scatter=False, color=sns.color_palette("Paired")[1], ax=ax6)
    ax6.set_title("Price vs Volume", fontsize=6)
    ax6.set_xlabel("Price ($)", fontsize=6)
    ax6.set_ylabel("Volume", fontsize=6)
    ax6.tick_params(axis='both', labelsize=6)
    st.pyplot(fig6)
