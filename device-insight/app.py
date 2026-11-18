import hashlib
import io
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError

from core import demo_reports, validate_reports, fit_model, search_reports, theme_counts, run_agent
from api_config import resolve_api_key, key_problem, public_api_error

load_dotenv()
st.set_page_config(page_title='Device Insight | Checkpoint 2', page_icon='🔎', layout='wide')
st.markdown('''<style>
    .stApp {background: #f6f8fc;}
    h1,h2,h3 {color: #12344a;}
    [data-testid="stMetric"] {background:white;padding:18px;border-radius:12px;}
    .block-container {padding-top:2rem;}
</style>''', unsafe_allow_html=True)


@st.cache_resource(show_spinner='Fitting TF-IDF and K-Means...')
def train(csv_bytes, k):
    df = pd.read_csv(io.BytesIO(csv_bytes), dtype=str, keep_default_na=False)
    return fit_model(df, k)


st.title('Device Insight')
st.caption('DESIGNTK 530 · Checkpoint 2 · Explore reports, discover themes, ask evidence-based questions')

with st.sidebar:
    st.header('Workspace')
    page = st.radio('Navigate', ['Explore reports', 'AI research assistant', 'ML dashboard', 'About & demo'])
    options = ['Fictional demo', 'Upload prepared CSV']
    local_reports = Path(__file__).with_name('local-reports.csv')
    if local_reports.exists():
        options.insert(0, 'Local MAUDE ZIP subset')
    source = st.radio('Data source', options)
    upload = None
    if source == 'Upload prepared CSV':
        upload = st.file_uploader('Prepared report CSV', type='csv')
        st.caption('4–5,000 rows. See README for required columns. Raw MAUDE ZIP files need preprocessing.')
    k = st.slider('Number of ML themes (K)', 2, 8, 5)
    st.caption('Changing K refits K-Means and updates report filters and AI tools.')

if source == 'Upload prepared CSV':
    if upload is None:
        st.info('Upload a prepared CSV, or switch to Fictional demo to try the app immediately.')
        st.stop()
    if upload.size > 15 * 1024 * 1024:
        st.error('Please use a CSV smaller than 15 MB.')
        st.stop()
    try:
        base = validate_reports(pd.read_csv(upload, dtype=str, keep_default_na=False))
    except (ValueError, pd.errors.ParserError, UnicodeDecodeError, pd.errors.EmptyDataError) as exc:
        st.error(f'Could not load CSV: {exc}')
        st.stop()
elif source == 'Local MAUDE ZIP subset':
    try:
        base = validate_reports(pd.read_csv(local_reports, dtype=str, keep_default_na=False))
        base['source'] = 'Local MAUDE ZIP subset (provenance unverified)'
    except (ValueError, pd.errors.ParserError) as exc:
        st.error(f'Could not load the local subset: {exc}')
        st.stop()
else:
    base = demo_reports()

is_demo = source == 'Fictional demo'
if is_demo:
    st.warning('FICTIONAL DEMO DATA — Invented devices and narratives. These are not FDA reports or clinical evidence.')
elif source == 'Local MAUDE ZIP subset':
    st.info('Local ZIP subset · Up to 300 joined reports from your 2025 device and narrative ZIPs. '
            'Convenience sample, not representative; local file provenance has not been independently verified. '
            'Only the first narrative per report is included. Event type was not loaded from the master table.')
else:
    st.info('Uploaded CSV · Source and completeness are user-supplied and have not been verified.')
st.caption('Research prototype. Report counts do not measure failure rates or prove causality. '
           'This app does not recommend whether to use a device or submit reports to FDA.')

csv_bytes = base.to_csv(index=False).encode()
try:
    df, vectorizer, matrix, km, score = train(csv_bytes, k)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    device = st.selectbox('Device scope', ['All devices'] + sorted(df.device.unique().tolist()))
    events = st.multiselect('Event type scope', sorted(df.event_type.unique()), default=sorted(df.event_type.unique()))

mask = df.event_type.isin(events)
if device != 'All devices':
    mask &= df.device.eq(device)
indices = df.index[mask].to_numpy()
scope = df.loc[mask].reset_index(drop=True)
scope_matrix = matrix[indices]
fingerprint = hashlib.sha256(csv_bytes + str((k, device, events)).encode()).hexdigest()
if st.session_state.get('fingerprint') != fingerprint:
    st.session_state.pop('agent_result', None)
    st.session_state['fingerprint'] = fingerprint

a, b, c = st.columns(3)
a.metric('Reports in scope', len(scope))
b.metric('Devices in scope', scope.device.nunique())
c.metric('Themes in scope', scope.cluster.nunique())


def display_report(row):
    with st.expander(f"{row['report_id']} · {row['device']}"):
        st.write(f"Manufacturer: {row['manufacturer']}")
        st.write(f"Event type: {row['event_type']}")
        st.write(f"ML group: {row['theme']}")
        st.text(row['narrative'])
        st.caption(f"Source: {row['source']}")


if page == 'Explore reports':
    st.subheader('Find a reported experience')
    st.write('Search by device, report ID, or narrative words. Open a result to inspect the source text.')
    query = st.text_input('Search reports', placeholder='Try battery, adhesive, Bluetooth, or DEMO-001', max_chars=500)
    theme = st.selectbox('Filter by ML theme', ['All themes'] + sorted(scope.theme.unique().tolist()))
    submask = scope.theme.eq(theme) if theme != 'All themes' else pd.Series(True, index=scope.index)
    sub = scope[submask].reset_index(drop=True)
    submatrix = scope_matrix[scope.index[submask].to_numpy()]
    matches = search_reports(sub, vectorizer, submatrix, query, limit=100) if len(sub) else sub
    st.caption(f'{len(matches)} results shown (maximum 100). Search uses lexical TF-IDF similarity, not semantic embeddings.')
    if matches.empty:
        st.info('No matching reports. Try another word or widen your filters.')
    for row in matches.to_dict('records'):
        display_report(row)
    st.download_button('Download these results', matches.to_csv(index=False), 'report-results.csv', 'text/csv')

elif page == 'AI research assistant':
    st.subheader('Ask the report research assistant')
    st.write('The assistant chooses tools to search the selected reports and inspect ML themes, then explains '
             'its findings with report IDs. It can retry searches using different words.')
    configured_key = os.getenv('OPENAI_API_KEY', '').strip()
    if configured_key == 'replace-with-your-api-key':
        configured_key = ''
    entered_key = st.text_input('OpenAI API key', type='password',
                                help='Used for this browser session only. You can also configure OPENAI_API_KEY in .env.')
    api_key = resolve_api_key(entered_key, configured_key)
    problem = key_problem(api_key)
    if entered_key.strip():
        st.caption('Using the key entered above. It overrides .env/server settings; no restart is needed.')
    elif api_key:
        st.caption('Using the configured server key. Enter a key above to override it without restarting.')
    st.markdown('[Create or manage OpenAI API keys](https://platform.openai.com/api-keys)')
    if problem:
        st.error(problem)
    model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini').strip() or 'gpt-4.1-mini'
    st.caption(f'Model: {model} · Up to four tool rounds plus a final answer')
    if not api_key:
        st.info('LLM is not connected yet. Enter your API key above, or add OPENAI_API_KEY in .env and restart. '
                'Search and the ML dashboard already work without it. There is no simulated AI answer.')
    st.caption('Test API connection sends only a short test message to OpenAI, with no report data. API usage may incur charges.')
    if st.button('Test API connection', disabled=not api_key or bool(problem)):
        try:
            with st.spinner('Testing the key and model...'):
                test = OpenAI(api_key=api_key, timeout=30.0, max_retries=0).responses.create(
                    model=model, input='Reply with OK.', max_output_tokens=32, store=False)
            if test.output_text:
                st.success('Connection successful. Your key and selected model work; you can research reports below.')
            else:
                st.warning('The API accepted the request but returned no text. Try researching a report question.')
        except (AuthenticationError, RateLimitError, APIConnectionError, APIStatusError) as exc:
            st.error(public_api_error(exc))
    with st.form('ask'):
        question = st.text_area('Your question', 'What battery and charging issues appear in these reports?', max_chars=1500)
        consent = st.checkbox('Send my question and retrieved report excerpts to OpenAI. I will use only public or fictional data without personal information.')
        submit = st.form_submit_button('Research selected reports', disabled=not api_key or bool(problem) or scope.empty)
    if submit:
        st.session_state.pop('agent_result', None)
        if not question.strip():
            st.error('Enter a question.')
        elif not consent:
            st.error('Confirm the data-sharing checkbox before running the assistant.')
        else:
            with st.status('Researching reports...', expanded=True) as status:
                try:
                    client = OpenAI(api_key=api_key, timeout=45.0, max_retries=1)
                    def update(entry):
                        st.write(f"Step {entry['step']}: {entry['tool']} {json.dumps(entry['arguments'])}")
                    result = run_agent(client, model, question.strip(), scope, vectorizer, scope_matrix, update)
                    st.session_state['agent_result'] = dict(result, question=question, data_source=source, device_scope=device)
                    status.update(label='Research complete', state='complete', expanded=False)
                except (AuthenticationError, RateLimitError, APIConnectionError, APIStatusError) as exc:
                    status.update(label=public_api_error(exc), state='error')
                except (ValueError, KeyError, TypeError) as exc:
                    status.update(label=f'Could not complete the research: {exc}', state='error')
    result = st.session_state.get('agent_result')
    if result:
        st.caption('Answer for: ' + result['question'])
        answer = result['answer']
        st.markdown('#### Summary')
        st.write(answer['summary'])
        st.markdown('#### Observations and citations')
        if not answer['observations']:
            st.info('No supported observations returned. Try a broader search.')
        for observation in answer['observations']:
            st.write(observation['text'])
            st.caption('Reports: ' + ', '.join(observation['report_ids']))
        st.markdown('#### Limitations')
        st.write(answer['limitations'])
        st.caption('Report IDs were checked against retrieved evidence. This does not automatically verify every generated claim.')
        with st.expander('Agent workflow: actual tool calls and outputs'):
            st.json(result['trace'])
        st.markdown('#### Inspect retrieved evidence')
        for row in result['evidence']:
            full = scope[scope.report_id.eq(row['report_id'])].iloc[0].to_dict()
            display_report(full)
        st.download_button('Download answer + workflow evidence', json.dumps(result, indent=2), 'research-session.json', 'application/json')

elif page == 'ML dashboard':
    st.subheader('Traditional machine learning: report themes')
    st.write('TF-IDF converts narrative words and word pairs into numerical features. K-Means then learns '
             'groups of similar narratives. Theme labels come from the three highest-weight terms in each centroid.')
    st.caption('Model fits the entire loaded dataset. Charts and examples respect the sidebar scope. '
               'Groups reflect wording, not verified root causes or clinical severity.')
    x, y, z = st.columns(3)
    x.metric('Training reports', len(df))
    y.metric('Learned features', matrix.shape[1])
    z.metric('Fitted clusters', km.n_clusters)
    st.write(f'Cosine silhouette score: {score:.3f}' if score is not None else 'Silhouette score: unavailable for this dataset.')
    st.caption('Silhouette measures separation of the learned groups, not clinical validity or prediction accuracy. '
               'For more than 1,000 reports, it uses a reproducible sample of 1,000. '
               'No labeled ground truth or held-out clinical evaluation is included.')
    if len(scope):
        counts = pd.DataFrame(theme_counts(scope)).set_index('theme')
        st.bar_chart(counts, horizontal=True)
        chosen = st.selectbox('Inspect a learned theme', sorted(scope.theme.unique()))
        examples = scope[scope.theme.eq(chosen)]
        st.caption(f'{len(examples)} reports in this group within your scope. Showing up to 20.')
        for row in examples.head(20).to_dict('records'):
            display_report(row)
    st.download_button('Download all cluster assignments', df.to_csv(index=False), 'clustered-reports.csv', 'text/csv')

else:
    st.subheader('Checkpoint 2 demonstration')
    st.markdown('''
1. **Interface:** open Explore reports, search `battery`, filter a device, and expand a report.
2. **Traditional ML:** open ML dashboard, inspect theme keywords and examples, then change K in the sidebar.
3. **Agent + LLM:** open AI research assistant, ask about battery issues, confirm data sharing, and run research.
4. Expand the workflow to show real tool calls, inspect the cited reports, and download the research session.

**Architecture:** prepared CSV / fictional examples → TF-IDF → K-Means + lexical search →
model-selected local tools → evidence-linked explanation → interface.

**Current scope:** read-only report exploration. No FDA submission, email, ratings, sales contacts,
live MAUDE sync, clinical recommendations, or device safety rankings are implemented.

**Data continuity:** upload a prepared, de-identified MAUDE CSV to replace the demo examples.
The raw multi-file MAUDE ZIP must be joined and cleaned outside this app first.
The demo alone does not establish dataset continuity with MAUDE.

**Persistence:** uploaded data and answers remain in the running session; they are not a permanent database.
Download results before closing or refreshing. API requests use `store=False`.
''')
    st.download_button('Download fictional example CSV / column template', demo_reports().to_csv(index=False), 'fictional-example-reports.csv', 'text/csv')
