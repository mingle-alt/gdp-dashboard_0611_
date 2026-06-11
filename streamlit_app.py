import streamlit as st
import pandas as pd
import math
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title='GDP dashboard',
    page_icon=':earth_americas:',
)

@st.cache_data
def get_gdp_data():
    DATA_FILENAME = Path(__file__).parent / 'data/gdp_data.csv'
    raw_gdp_df = pd.read_csv(DATA_FILENAME)

    MIN_YEAR = 1960
    MAX_YEAR = 2022

    # wide → long 변환 (Country Name 포함)
    gdp_df = raw_gdp_df.melt(
        ['Country Name', 'Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        'Year',
        'GDP',
    )
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])
    gdp_df['GDP'] = pd.to_numeric(gdp_df['GDP'], errors='coerce')

    # 전년 대비 성장률 계산
    gdp_df = gdp_df.sort_values(['Country Code', 'Year'])
    gdp_df['GDP_Growth'] = gdp_df.groupby('Country Code')['GDP'].pct_change() * 100

    return gdp_df

gdp_df = get_gdp_data()

# 국가코드 → 국가명 매핑
code_to_name = gdp_df[['Country Code', 'Country Name']].drop_duplicates().set_index('Country Code')['Country Name'].to_dict()
name_to_code = {v: k for k, v in code_to_name.items()}

# -----------------------------------------------------------------------------
# 페이지 제목
'''
# :earth_americas: GDP dashboard

Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website.
'''

''
''

# -----------------------------------------------------------------------------
# 사이드바 필터
min_value = int(gdp_df['Year'].min())
max_value = int(gdp_df['Year'].max())

from_year, to_year = st.slider(
    'Which years are you interested in?',
    min_value=min_value,
    max_value=max_value,
    value=[min_value, max_value]
)

# 국가 선택 (국가명으로 표시)
all_country_names = sorted(code_to_name.values())
default_names = [code_to_name[c] for c in ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'] if c in code_to_name]

selected_names = st.multiselect(
    'Which countries would you like to view?',
    all_country_names,
    default_names
)

selected_codes = [name_to_code[n] for n in selected_names if n in name_to_code]

# 지표 선택
metric = st.radio(
    'Select metric',
    ['GDP (USD)', 'GDP Growth Rate (%)'],
    horizontal=True
)

use_growth = metric == 'GDP Growth Rate (%)'
value_col = 'GDP_Growth' if use_growth else 'GDP'
value_label = 'Growth Rate (%)' if use_growth else 'GDP (USD)'

''
''

if not selected_codes:
    st.warning("Select at least one country")
    st.stop()

# 데이터 필터링
filtered_df = gdp_df[
    (gdp_df['Country Code'].isin(selected_codes))
    & (gdp_df['Year'] >= from_year)
    & (gdp_df['Year'] <= to_year)
].copy()

# 차트용: Country Code → Country Name 으로 교체
filtered_df['Country'] = filtered_df['Country Code'].map(code_to_name)

def format_gdp(val):
    """GDP 값을 T/B 단위로 포맷."""
    if val >= 1e12:
        return f'${val/1e12:.2f}T'
    elif val >= 1e9:
        return f'${val/1e9:.1f}B'
    else:
        return f'${val:,.0f}'

COLORS = px.colors.qualitative.Bold

# -----------------------------------------------------------------------------
# 라인 차트
st.header(f'{value_label} over time', divider='gray')
''

chart_df = filtered_df[['Year', 'Country', value_col]].dropna(subset=[value_col])

if chart_df.empty:
    st.info("No data available for the selected range.")
else:
    if use_growth:
        fig_line = px.line(
            chart_df, x='Year', y=value_col, color='Country',
            color_discrete_sequence=COLORS,
            labels={value_col: 'Growth Rate (%)'},
        )
        fig_line.update_traces(
            hovertemplate='<b>%{fullData.name}</b><br>Year: %{x}<br>Growth: %{y:.2f}%<extra></extra>'
        )
        fig_line.update_layout(yaxis_ticksuffix='%')
    else:
        fig_line = px.line(
            chart_df, x='Year', y=value_col, color='Country',
            color_discrete_sequence=COLORS,
            labels={value_col: 'GDP (USD)'},
        )
        fig_line.update_traces(
            customdata=chart_df[value_col].apply(format_gdp),
            hovertemplate='<b>%{fullData.name}</b><br>Year: %{x}<br>GDP: %{customdata}<extra></extra>'
        )
        fig_line.update_layout(
            yaxis=dict(tickformat='.2s', tickprefix='$')
        )

    fig_line.update_layout(
        plot_bgcolor='white',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        margin=dict(t=60, b=40),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor='#f0f0f0'),
    )
    st.plotly_chart(fig_line, use_container_width=True)

''
''

# -----------------------------------------------------------------------------
# 막대 차트 (선택 기간 마지막 연도 기준)
st.header(f'{value_label} comparison in {to_year}', divider='gray')
''

bar_df = filtered_df[filtered_df['Year'] == to_year][['Country', value_col]].dropna(subset=[value_col])
bar_df = bar_df.sort_values(value_col, ascending=False)

if bar_df.empty:
    st.info(f"No data available for {to_year}.")
else:
    if use_growth:
        text_vals = bar_df[value_col].map(lambda x: f'{x:+.2f}%')
        tickformat, ticksuffix, tickprefix = '.1f', '%', ''
    else:
        text_vals = bar_df[value_col].map(format_gdp)
        tickformat, ticksuffix, tickprefix = '.2s', '', '$'

    fig_bar = px.bar(
        bar_df, x='Country', y=value_col,
        color='Country', color_discrete_sequence=COLORS,
        text=text_vals,
        labels={value_col: value_label},
    )
    fig_bar.update_traces(
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>' + value_label + ': %{text}<extra></extra>',
    )
    fig_bar.update_layout(
        plot_bgcolor='white',
        showlegend=False,
        margin=dict(t=40, b=40),
        xaxis=dict(showgrid=False),
        yaxis=dict(
            gridcolor='#f0f0f0',
            tickformat=tickformat,
            ticksuffix=ticksuffix,
            tickprefix=tickprefix,
        ),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

''
''

# -----------------------------------------------------------------------------
# 순위 테이블
st.header(f'Country Rankings in {to_year}', divider='gray')
''

rank_df = filtered_df[filtered_df['Year'] == to_year][['Country', value_col]].dropna(subset=[value_col]).copy()
rank_df = rank_df.sort_values(value_col, ascending=False).reset_index(drop=True)
rank_df.index += 1
rank_df.index.name = 'Rank'

if use_growth:
    rank_df[value_col] = rank_df[value_col].map(lambda x: f'{x:+.2f}%')
else:
    rank_df[value_col] = rank_df[value_col].map(lambda x: f'${x/1e9:,.1f}B')

rank_df.columns = ['Country', value_label]

if rank_df.empty:
    st.info(f"No data available for {to_year}.")
else:
    st.dataframe(rank_df, use_container_width=True)

''
''

# -----------------------------------------------------------------------------
# 메트릭 카드
st.header(f'GDP in {to_year}', divider='gray')
''

cols = st.columns(4)

first_year_df = gdp_df[gdp_df['Year'] == from_year]
last_year_df = gdp_df[gdp_df['Year'] == to_year]

for i, code in enumerate(selected_codes):
    col = cols[i % len(cols)]
    country_name = code_to_name.get(code, code)

    first_row = first_year_df[first_year_df['Country Code'] == code]['GDP']
    last_row = last_year_df[last_year_df['Country Code'] == code]['GDP']

    first_gdp = first_row.iloc[0] / 1e9 if len(first_row) > 0 and not pd.isna(first_row.iloc[0]) else None
    last_gdp = last_row.iloc[0] / 1e9 if len(last_row) > 0 and not pd.isna(last_row.iloc[0]) else None

    with col:
        if last_gdp is None:
            st.metric(label=f'{country_name} GDP', value='N/A', delta=None)
        elif first_gdp is None or first_gdp == 0:
            st.metric(label=f'{country_name} GDP', value=f'{last_gdp:,.0f}B', delta='n/a', delta_color='off')
        else:
            growth = f'{last_gdp / first_gdp:,.2f}x'
            st.metric(label=f'{country_name} GDP', value=f'{last_gdp:,.0f}B', delta=growth)
