from pathlib import Path
import hashlib
import html
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from chart_data import METRICS, trend_grid

st.set_page_config(page_title='MAUDE | Device reporting explorer', page_icon='◈', layout='wide')
ROOT = Path(__file__).parent
COLORS = ['#007F78','#D05C30','#5666B0','#9B4777','#427BA0','#A07616','#477D41','#A34343','#685290','#526F79']
DASHES = ['solid','dash','dot','dashdot','longdash','longdashdot']

@st.cache_data
def load_data():
    return pd.read_csv(ROOT/'data/device_trends.csv'), pd.read_csv(ROOT/'data/company_year.csv')

try:
    data, company_data = load_data()
except (OSError, ValueError) as exc:
    st.error(f'Could not load the prepared CSVs. Keep the data folder beside app.py. {exc}')
    st.stop()

companies = sorted(company_data.ANALYSIS_COMPANY.unique().tolist())
palette = dict(zip(companies, COLORS))
pairs_table = data.groupby(['ANALYSIS_COMPANY','GENERIC_DEVICE_TYPE'], as_index=False).DEVICE_RECORD_COUNT.sum()
pairs_table = pairs_table.sort_values(['DEVICE_RECORD_COUNT','ANALYSIS_COMPANY','GENERIC_DEVICE_TYPE'], ascending=[False,True,True])
available_pairs = set(zip(pairs_table.ANALYSIS_COMPANY,pairs_table.GENERIC_DEVICE_TYPE))
original_pairs = {
    ('BD','PUMP, INFUSION'),
    ('Medtronic','AUTOMATED INSULIN DOSING DEVICE SYSTEM, SINGLE HORMONAL CONTROL'),
    ('Medtronic','ARTIFICIAL PANCREAS DEVICE SYSTEM, SINGLE HORMONAL CONTROL'),
    ('Abbott','FLASH GLUCOSE MONITORING SYSTEM'),
    ('Medtronic','PUMP, INFUSION, INSULIN, TO BE USED WITH INVASIVE GLUCOSE SENSOR'),
}
if 'selected_pairs' not in st.session_state:
    st.session_state.selected_pairs = original_pairs & available_pairs
    st.session_state.initialized_companies = {'BD','Medtronic','Abbott'}
    st.session_state.editor_version = 0

def reset():
    st.session_state.companies = ['Abbott','BD','Medtronic']
    st.session_state.years = list(range(2021,2026))
    st.session_state.metric = next(iter(METRICS))
    st.session_state.selected_pairs = original_pairs & available_pairs
    st.session_state.initialized_companies = {'BD','Medtronic','Abbott'}
    st.session_state.search = ''
    st.session_state.editor_version += 1
    for key in list(st.session_state):
        if key.startswith('device_editor_'):
            del st.session_state[key]

def update_checks(key, visible_pairs):
    chosen = set(st.session_state.selected_pairs)
    for index, changes in st.session_state[key].get('edited_rows',{}).items():
        if 'Show' in changes:
            pair = visible_pairs[int(index)]
            if changes['Show']:
                chosen.add(pair)
            else:
                chosen.discard(pair)
    st.session_state.selected_pairs = chosen
    st.session_state.editor_version += 1

st.markdown('**MAUDE / 2021–2025**')
st.title('Explore device reporting patterns')
st.write('How can patterns in medical-device reports help improve how users communicate problems to manufacturers?')
st.caption('For providers, patients, and medical-device designers exploring reported device experiences.')
st.info('Main conclusion: the reporting patterns and narrative examples support exploring an easier way to communicate device problems, with clear device details, use context, and care effects. Better reporting and improved patient outcomes still need to be tested.')
st.caption('Whole-dataset finding · all ten companies, 2021–2025: BD and Medtronic account for 64.0% of 4,779,852 device records. This statement does not change with the filters below.')
st.caption('These are device-record summaries of adverse-event reporting. They do not measure device safety or adverse-event incidence.')
active_companies = st.pills('Companies · click to turn on or off', companies, selection_mode='multi',
                            default=['Abbott','BD','Medtronic'], key='companies')
for company in active_companies:
    if company not in st.session_state.initialized_companies:
        top = pairs_table.loc[pairs_table.ANALYSIS_COMPANY.eq(company)].iloc[0]
        st.session_state.selected_pairs.add((company, top.GENERIC_DEVICE_TYPE))
        st.session_state.initialized_companies.add(company)

c1,c2,c3 = st.columns([2,2,1])
with c1:
    metric = st.selectbox('Graph measure', list(METRICS), key='metric')
with c2:
    years = st.multiselect('Years to display', list(range(2021,2026)), default=list(range(2021,2026)), key='years')
with c3:
    st.write('')
    st.button('Reset comparison', on_click=reset, use_container_width=True)
if not active_companies or not years:
    st.info('Select at least one company and one year to see the comparison.')
    st.stop()

filtered_totals = company_data.loc[company_data.ANALYSIS_COMPANY.isin(active_companies) & company_data.YEAR.isin(years)]
m1,m2,m3 = st.columns(3)
m1.metric('Companies selected', len(active_companies))
m2.metric('Years selected', len(years))
m3.metric('All device records · selected companies / years', f'{filtered_totals.DEVICE_RECORD_COUNT.sum():,}')
st.divider()
chart_col, side_col = st.columns([2.2,1.3], gap='large')
with side_col:
    st.subheader('Choose device trends')
    st.caption('Check Show to add a line. Selections stay saved when a company is off.')
    search = st.text_input('Search device names', placeholder='Try infusion, glucose, pacemaker…', key='search')
    candidates = pairs_table.loc[pairs_table.ANALYSIS_COMPANY.isin(active_companies)].copy()
    if search.strip():
        candidates = candidates.loc[candidates.GENERIC_DEVICE_TYPE.str.contains(search.strip(), case=False, regex=False)]
    visible = candidates.head(60).copy()
    # Without a search, keep all active checked rows visible even below rank 60.
    if not search.strip():
        selected_rows = candidates.loc[[pair in st.session_state.selected_pairs for pair in zip(candidates.ANALYSIS_COMPANY,candidates.GENERIC_DEVICE_TYPE)]]
        visible = pd.concat([selected_rows,visible]).drop_duplicates(['ANALYSIS_COMPANY','GENERIC_DEVICE_TYPE'])
    visible_pairs = list(zip(visible.ANALYSIS_COMPANY, visible.GENERIC_DEVICE_TYPE))
    totals = data.loc[data.YEAR.isin(years)].groupby(['ANALYSIS_COMPANY','GENERIC_DEVICE_TYPE']).DEVICE_RECORD_COUNT.sum()
    table = pd.DataFrame({
        'Show':[p in st.session_state.selected_pairs for p in visible_pairs],
        'Company':[p[0] for p in visible_pairs], 'Device type':[p[1] for p in visible_pairs],
        'Records':[int(totals.get(p,0)) if p in totals.index else None for p in visible_pairs],
    })
    table['Show'] = table['Show'].astype(bool)
    digest = hashlib.sha256(repr((visible_pairs, sorted(years), st.session_state.editor_version)).encode()).hexdigest()[:16]
    editor_key = 'device_editor_' + digest
    st.data_editor(table, key=editor_key, hide_index=True, use_container_width=True, height=430,
                   disabled=['Company','Device type','Records'],
                   column_config={'Show':st.column_config.CheckboxColumn('Show',width='small'),
                                  'Device type':st.column_config.TextColumn('Device type',width='large'),
                                  'Records':st.column_config.NumberColumn('Records',format='%d', help='Selected years; blank means no source row.')},
                   on_change=update_checks, args=(editor_key,visible_pairs))
    st.caption(f'{len(visible):,} of {len(candidates):,} matching company/device pairs shown. Search to reach any device name. Ordering uses 2021–2025 volume; counts use selected years.')

chosen = {p for p in st.session_state.selected_pairs if p[0] in active_companies}
grid = trend_grid(data,chosen,years)
value_col, y_title = METRICS[metric]
with chart_col:
    st.subheader('Device trends over time')
    if metric == 'Share within company (%)':
        st.caption('Device-category records ÷ all records for the same company and year × 100. Selecting fewer categories does not change the denominator.')
    elif metric == 'Change since 2021':
        st.caption('Each company/device starts at 100 in 2021. A value of 150 means 50% more device records. Missing or zero 2021 baselines cannot be indexed.')
    else:
        st.caption('The original record volumes, without normalization.')
    if not chosen:
        st.info('Check a device trend in the table to add a line.')
    else:
        fig = go.Figure()
        device_styles = {device:DASHES[i % len(DASHES)] for i,device in enumerate(sorted({p[1] for p in chosen}))}
        for company,device in sorted(chosen):
            part = grid.loc[grid.ANALYSIS_COMPANY.eq(company) & grid.GENERIC_DEVICE_TYPE.eq(device)]
            fig.add_trace(go.Scatter(x=part.YEAR,y=part[value_col],mode='lines+markers',
                name=f'{company} · {device}',connectgaps=False,
                line={'color':palette[company],'dash':device_styles[device],'width':2.6},
                marker={'size':7},customdata=part[['DEVICE_RECORD_COUNT','COMPANY_YEAR_TOTAL','PERCENT_OF_COMPANY_YEAR']],
                hovertemplate='<b>'+company+' · '+device+'</b><br>Year %{x}<br>Value: %{y:,.2f}<br>Device records: %{customdata[0]:,.0f}<br>Company-year total: %{customdata[1]:,.0f}<br>Company-year share: %{customdata[2]:.2f}%<extra></extra>'))
        fig.update_layout(height=480,margin=dict(l=10,r=20,t=15,b=30),template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',showlegend=False,
            xaxis=dict(title='Year',tickmode='array',tickvals=list(range(2021,2026)),range=[2020.8,2025.2]),
            yaxis=dict(title=y_title,rangemode='tozero',gridcolor='#DFE7EC'),hoverlabel=dict(namelength=-1))
        if metric == 'Change since 2021':
            fig.add_hline(y=100,line_dash='dot',line_color='#87949D')
        st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False,'toImageButtonOptions':{'filename':'maude_device_trends','scale':2}})
        st.caption('Color identifies the company; line style distinguishes device types. Hover to identify a line. Missing rows and excluded years are gaps.')
        if len(chosen)>12:
            st.info('More than 12 lines are selected. Turn some off to make the comparison easier to read.')
        if grid[value_col].notna().sum()==0:
            st.info('No values are available for these selections and this measure. Try record counts or another year.')
        st.markdown('**Selected lines**')
        for company,device in sorted(chosen):
            st.markdown(f'<span style="color:{palette[company]}">●</span> <b>{html.escape(company)}</b> · {html.escape(device)} · {device_styles[device]}', unsafe_allow_html=True)
        download = grid.loc[grid.YEAR_INCLUDED].drop(columns='YEAR_INCLUDED')
        st.download_button('Download selected trend data',download.to_csv(index=False),'selected_maude_trends.csv','text/csv')

st.divider()
st.subheader('Explore the original summaries')
tab_devices,tab_companies,tab_outcomes,tab_narratives,tab_sensitivity,tab_project,tab_method = st.tabs(['Device categories','Companies','Outcome snapshot','Text findings','Sensitivity','Project conclusions','How to read this'])
subset = data.loc[data.ANALYSIS_COMPANY.isin(active_companies) & data.YEAR.isin(years)]
with tab_devices:
    st.caption('Top ten device categories by raw device-record volume for the selected companies and years. The trend checkboxes do not filter this overview.')
    top = subset.groupby('GENERIC_DEVICE_TYPE',as_index=False).DEVICE_RECORD_COUNT.sum().nlargest(10,'DEVICE_RECORD_COUNT').sort_values('DEVICE_RECORD_COUNT')
    figure = px.bar(top,x='DEVICE_RECORD_COUNT',y='GENERIC_DEVICE_TYPE',orientation='h',color_discrete_sequence=['#007F78'],labels={'DEVICE_RECORD_COUNT':'Device records','GENERIC_DEVICE_TYPE':'Device category'})
    figure.update_layout(height=530,margin=dict(l=10,r=20,t=10,b=20))
    st.plotly_chart(figure,use_container_width=True)
    if not top.empty:
        leading = top.iloc[-1]
        st.write(f"For the selected companies and years, {leading.GENERIC_DEVICE_TYPE} has the largest included count: {int(leading.DEVICE_RECORD_COUNT):,} device records. This identifies reporting concentration within the selection.")
with tab_companies:
    st.caption('Total device records for selected years. This is reporting volume, not an industry or safety ranking.')
    ranked = filtered_totals.groupby('ANALYSIS_COMPANY',as_index=False).DEVICE_RECORD_COUNT.sum().sort_values('DEVICE_RECORD_COUNT')
    figure = px.bar(ranked,x='DEVICE_RECORD_COUNT',y='ANALYSIS_COMPANY',orientation='h',color='ANALYSIS_COMPANY',color_discrete_map=palette,labels={'DEVICE_RECORD_COUNT':'Device records','ANALYSIS_COMPANY':'Company'})
    figure.update_layout(showlegend=False,height=430)
    st.plotly_chart(figure,use_container_width=True)
with tab_outcomes:
    st.caption('Fixed 2021–2025 snapshot recovered from the saved table in notebook cell 18. Company, year, and device filters do not apply: this table has no breakdown by those fields. Counts are outcome entries, not unique patients or reports.')
    outcomes = pd.read_csv(ROOT/'data/outcomes_notebook_snapshot.csv')
    figure = px.pie(outcomes,values='OUTCOME_ENTRY_COUNT',names='REPORTED_PATIENT_OUTCOME',hole=.5,
                    color_discrete_sequence=['#007F78','#657A8C','#D89A36','#C85B51','#7662A2','#427BA0','#B06D92'])
    figure.update_traces(textinfo='percent',hovertemplate='%{label}<br>%{value:,.0f} outcome entries<br>%{percent}<extra></extra>')
    figure.update_layout(height=430)
    st.plotly_chart(figure,use_container_width=True)
    st.dataframe(outcomes,hide_index=True,use_container_width=True)
with tab_narratives:
    st.markdown('**What the text adds:** care disruption and use context help explain what a reporting form should capture. The proposed form should ask what happened, what staff did next, and which information is unavailable.')
    coding = pd.read_csv(ROOT/'data/narrative_coding.csv',dtype={'MDR_REPORT_KEY':str})
    coding_dates = pd.to_datetime(coding.DATE_REPORT,errors='coerce')
    coding = coding.loc[coding.ANALYSIS_COMPANY.isin(active_companies) & coding_dates.dt.year.isin(years)]
    code_labels = {'CARE_DISRUPTION_OR_ACTION':'Care disruption or corrective action','USE_OR_INFORMATION_CONTEXT':'Use, setup, or information gaps','EXPLICIT_NO_REPORTED_HARM':'Explicit absence of reported harm'}
    st.caption(f'Filtered qualitative sample: {len(coding)} excerpts, selected companies and narrative dates. The full sample has 30 excerpts, three per company, all dated 2025. Themes overlap. AI-assisted annotations await author review.')
    if coding.empty:
        st.info('No narrative excerpts match these filters. The supplied sample is dated 2025.')
    else:
        theme_summary = pd.DataFrame([{'Theme':label,'Coded excerpts':int(coding[col].sum())} for col,label in code_labels.items()])
        figure = px.bar(theme_summary,x='Coded excerpts',y='Theme',orientation='h',color_discrete_sequence=['#007F78'])
        figure.update_xaxes(range=[0,max(len(coding),1)],dtick=max(1,len(coding)//6))
        st.plotly_chart(figure,use_container_width=True)
    st.markdown('''**Whole-sample examples (unfiltered):** MDR **22206171** describes a footswitch workaround, and **21545385** describes a 90-minute delay. MDR **22064912** notes that additional information was requested. These examples support prompts for care effects and missing context.

**Counterexamples:** MDR **21968342** explicitly reports no adverse patient effects or significant delay. MDR **21659766** describes positioning as a factor. A device complaint alone does not establish intrinsic device failure or patient harm. These excerpts quote the supplied sample, not verified verbatim FDA text.''')
    st.caption('The supplied 30-row sample is illustrative. It is not a representative estimate of problem frequency; text is displayed as supplied and has not been verified as verbatim FDA text. Year filtering here uses DATE_REPORT.')
    narratives = pd.read_csv(ROOT/'data/narratives.csv',dtype={'MDR_REPORT_KEY':str})
    dates = pd.to_datetime(narratives.DATE_REPORT,errors='coerce')
    narratives = narratives.loc[narratives.ANALYSIS_COMPANY.isin(active_companies) & dates.dt.year.isin(years)]
    st.dataframe(narratives,hide_index=True,use_container_width=True,column_config={'SOURCE_URL':st.column_config.LinkColumn('FDA record')})
    if st.checkbox('Show the notebook’s exploratory keyword chart'):
        themes = {
            'Device malfunction':['malfunction','failed','failure','broken','leak','error','alarm'],
            'Patient outcomes':['injury','pain','bleeding','infection','hospitalized','hospitalization','death','symptom','burn','swelling'],
            'Difficulty using device':['difficult','difficulty','unable','setup','instructions','connect','operate','operation','use'],
        }
        text = narratives.TEXT.fillna('').str.lower()
        counts = pd.DataFrame([{'Theme':label,'Matching sample rows':int(text.map(lambda t:any(word in t for word in words)).sum())} for label,words in themes.items()])
        st.caption('Reproduces the notebook’s substring matching. Themes can overlap; negation and context are ignored, and broad terms such as “use” can produce false matches. These are unvalidated keyword flags.')
        figure = px.bar(counts,x='Matching sample rows',y='Theme',orientation='h',color_discrete_sequence=['#657A8C'])
        figure.update_xaxes(dtick=1)
        st.plotly_chart(figure,use_container_width=True)
with tab_sensitivity:
    st.caption('Fixed analysis of all supplied years. The company, year, and device filters above do not apply to this comparison.')
    st.dataframe(pd.read_csv(ROOT/'data/sensitivity.csv'),hide_index=True,use_container_width=True)
    st.write('Using the five largest companies retains 92.7% of records and the same leading category. Excluding BD changes the leader from infusion pumps to the automated insulin-dosing category. Reporting concentration persists, but which device type leads depends on the companies included.')
with tab_project:
    st.markdown('''
**The project argument.** Providers and patients may benefit from an easier way to review device experiences and communicate problems to manufacturers. The proposed website would organize products and support feedback with device/model or lot information when available.

**What the evidence supports.** The quantitative summaries show where the included device records concentrate and how each company's device mix changes over time. Narrative examples add care effects, workarounds, and information that may help an investigation. Those examples suggest useful reporting prompts; they do not establish whether manufacturers currently overlook reports.

**The proposed next step.** The official project proposes comparing the website without its new reporting/review feature (A) with a version that includes the feature (B). Check whether reporting becomes easier and produces clearer, useful information while watching for duplicates, missing details, and unsupported device blame. This dashboard describes existing evidence; it does not contain experiment results.

**Adopt, retain, or revise.** Before attributing a benefit to B, check comparable users, opportunities, instructions, and observation periods. Adopt if the feature makes reporting easier and yields clearer information. Retain A if the benefit is small or reporting becomes confusing. Revise and test again when user feedback identifies fixable problems.

**What remains uncertain.** The summaries do not establish device incidence, causes of spikes, manufacturer turnaround, or improved patient outcomes. Interviews, more representative text sampling, and the proposed A/B study would help assess the communication need. Device-use denominators and verified category mappings would be needed for stronger device comparisons.
''')
with tab_method:
    st.markdown('''
**What the percentages mean.** Each device category is divided by all device records for that same company and year. This describes the mix of records within a company. Companies have different product portfolios, so these percentages are not like-for-like device risk comparisons. A share can rise because other categories fell.

**What was checked.** All 50 company/year totals reconcile with the device-summary rows. Existing percentages match to their supplied rounding. The two device-summary uploads are identical and were used once. NA/N/A labels are grouped as Unknown / not specified, retaining their counts. Other device labels are preserved; aliases and clinical categories have not been merged.

**What the data cannot establish.** DEVICE_RECORD_COUNT is the source unit. These summaries contain no report IDs for deduplicating unique events, no device-use denominator, and no evidence establishing causation. The ten companies are the supplied study selection; their ranking among all companies is unverified. YEAR is retained as provided. Extraction date, date-field basis, and full-year coverage (including 2025) are unverified.

**Notebook scope.** The device and company bar charts and the selected company/device line chart have been recreated. The patient-outcomes CSV was not supplied; its seven-row saved output in notebook cell 18 was recovered as a fixed snapshot. It cannot be filtered by company or year. Keyword counts in the small narrative sample can misclassify phrases and are not used as validated outcome labels. Notebook claims that spikes were caused by recalls, regulatory changes, or adoption require separate evidence.

[FDA: MAUDE interpretation and limitations](https://open.fda.gov/data/maude/) · [Source MDR data files](https://www.fda.gov/medical-devices/medical-device-reporting-mdr-how-report-medical-device-problems/mdr-data-files)
''')
