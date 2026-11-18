# Device Insight — checkpoint two

A small Python + Streamlit application for exploring medical-device report narratives. It includes a real TF-IDF/K-Means implementation and a real OpenAI tool-calling integration. The supplied 36 reports are entirely fictional. No reports are sent to FDA.

## Exact GitHub Codespaces setup

1. Open your repository in GitHub. Click **Code → Codespaces → Create codespace on main** (or open your existing Codespace).
2. Download `device-insight-checkpoint2.zip` from the chat to your computer.
3. In Codespaces, open the **Explorer** on the left. Drag the ZIP into the repository file list. Alternatively, right-click the repository folder and select **Upload**.
4. Choose **Terminal → New Terminal** from the top menu. Paste these commands into the bottom terminal (not into a Python file):

```bash
unzip device-insight-checkpoint2.zip
cd device-insight
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

5. When Codespaces offers **Open in Browser**, click it. Otherwise, open the **Ports** tab beside Terminal, find port **8501**, and click its globe icon. If absent, click **Add Port** and enter **8501**. Keep the port private for your own demonstration.
6. Explore reports and ML dashboard work immediately with the fictional data.

If your ZIP uploaded with a different filename, substitute that exact filename in the first command. If `device-insight` already exists, use a fresh folder before extracting. If you close the terminal, restart with `cd device-insight`, `source .venv/bin/activate`, and the Streamlit command above; omit `cd` if already in that folder.

## Connect the real LLM

Easiest option: open **AI research assistant** in the running app and enter your API key in the password field. It is used for that browser session and is not written to a project file. The `.env` method below is an alternative.

Click **Test API connection** to check the key and selected model using a short test message with no report data. A pasted key takes precedence over server settings and needs no restart. Surrounding whitespace, an `OPENAI_API_KEY=` prefix, and surrounding quotes are removed automatically. A masked key from a key-list preview cannot be used; enter the complete secret value. A 401 rejection requires checking or replacing the supplied key at https://platform.openai.com/api-keys . Never paste a key into a chat or source-code file.

An API key with available API billing/credits and access to the chosen model is required. The app does not include a key. API requests can incur usage charges. Create/manage a key at https://platform.openai.com/api-keys .

1. In the Codespaces Explorer, expand **device-insight** and open **.env** (created by the commands above).
2. Replace the placeholder on the first line with your key. The file should have two lines:

```dotenv
OPENAI_API_KEY=your_actual_key_goes_here
OPENAI_MODEL=gpt-4.1-mini
```

3. Save with **Ctrl+S**. Do not paste your key into `app.py` or commit `.env` to GitHub. The supplied `.gitignore` excludes it.
4. Click in the terminal and press **Ctrl+C** to stop Streamlit. Paste:

```bash
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

5. Refresh the browser. Open **AI research assistant**, enter a question, check the data-sharing checkbox, and click **Research selected reports**.

You can instead create a Codespaces secret named `OPENAI_API_KEY` in GitHub settings and rebuild/restart the Codespace to make it available. Environment variables take precedence over `.env`. If the chosen model is unavailable to your account, change `OPENAI_MODEL` to a model you can access that supports Responses function calls and structured output, then restart.

## Where each piece of code belongs

The ZIP already contains the code in the correct files, so you do not have to copy hundreds of lines from chat. If creating the files manually, use **Explorer → New Folder → device-insight**, then create these files **inside that folder**, with these exact names:

| File | Purpose |
| --- | --- |
| `app.py` | The interface, navigation, filters, uploads, and result display |
| `core.py` | Data validation, sample data, TF-IDF, K-Means, search, and LLM tools |
| `requirements.txt` | Python packages installed by the terminal command |
| `.env.example` | Example API configuration; copy to `.env` for your own key |
| `.gitignore` | Prevents keys and temporary files being committed |
| `test_core.py` | Automated checks for ML, retrieval, validation, and agent dispatch |
| `test_ui.py` | Streamlit navigation and interaction checks |

Paste each downloaded file's contents into the Codespaces file with the same name. Terminal commands go only in the Terminal. Secret values go only in `.env` or Codespaces secrets.

## What to demonstrate for the professor

1. **Functional interface:** open Explore reports. Search `battery`. Filter to Demo Infusion Pump. Expand a report and inspect its narrative. Clear the search or change device scope to demonstrate navigation and empty states.
2. **Traditional machine learning:** open ML dashboard. Point out that TF-IDF fits narrative vocabulary, then K-Means learns groups. Inspect theme keywords and sample narratives. Change K from 5 to 3 and show the updated groups. Return to Explore reports and filter by a learned theme. Download the cluster CSV if desired.
3. **LLM + agent:** with an API key connected, open AI research assistant and ask: `What battery and charging issues appear in these reports?` Confirm data sharing and run it. Expand the workflow to show actual function calls. The model selects search words, can refine its search or request theme counts, receives local tool outputs, and generates an evidence-linked answer. Click cited report expanders to inspect the evidence. Download the JSON research session.
4. **Dataset continuity:** switch to Upload prepared CSV and upload a cleaned MAUDE subset when available. Show that the same interface and models work on your real project data. Until then, explicitly state that the data demonstration is fictional.

## Prepared CSV format

### Existing Codespace MAUDE files

`prepare_local_subset.py` streams a bounded join of `../data/530Final/device2025.zip` and `foitext2025.zip` by `MDR_REPORT_KEY`. Run `python prepare_local_subset.py` from this folder. It writes `local-reports.csv` and a selection manifest beside the app. When that CSV exists, **Local MAUDE ZIP subset** appears as the default source. The join considers the first 15,000 device rows and up to 100,000 eligible physical narrative rows, retains the first eligible narrative for each key, and stops at 300 reports. Malformed or overlong physical rows are skipped. Generic device name falls back to brand name. Event type is explicitly marked not loaded; the master report table is not joined. This is a convenience sample from user-supplied ZIPs, not a representative sample or independently verified FDA extract.

For another dataset, use the prepared CSV upload described below.

Use a UTF-8, comma-separated CSV with **4–5,000 rows**, under 15 MB. Required headers:

```csv
report_id,device,manufacturer,event_type,narrative
```

Every field must be nonempty. Each report ID must be unique; narratives may contain up to 20,000 characters. Use at least two distinct narratives with usable English words. Put narratives containing commas or newlines in CSV quotes; pandas exports this correctly. The About page offers a downloadable example/template.

This is a normalized input schema, not the raw MAUDE bulk-file schema. Raw MAUDE ZIP/text tables must be cleaned and joined by report key outside this app. Preserve source report IDs and source documentation. Do not upload identifiable patient details. The app treats uploaded provenance as unverified; it does not download or verify FDA records.

## Implementation and limitations

**User interface:** four navigable pages; case-insensitive literal device/ID search; lexical narrative retrieval; device/event/theme filters; report inspection; downloads; clear source labels and API error states.

**Traditional ML:** scikit-learn `TfidfVectorizer` fits unigrams and bigrams, up to 6,000 features. `KMeans` uses random seed 42 and 10 initializations. K is capped when an upload has too few distinct vectors. Theme names are the top three centroid terms. K-Means is unsupervised: this is not a trained safety classifier. Cosine silhouette is a descriptive separation metric on the same dataset (sampled at 1,000 reports), not held-out validation or clinical accuracy. The thematic grouping needs human review. Search uses cosine similarity over TF-IDF and exact metadata matches, not semantic embeddings. Similarity is not probability.

**Agent:** the first model call is constrained to call `search_reports`. Subsequent tool choices are model-driven, bounded to four tool rounds. `search_reports` and `get_theme_counts` use the selected device/event scope. The local app executes the calls and returns results to the model. A final structured-output call creates the answer. Cited IDs are validated against retrieved IDs; this does not establish semantic correctness. Each search returns at most six reports and 2,000 characters per narrative to the model; the interface retains full narratives. This is a small agent prototype, not a comprehensive evidence review.

**LLM privacy:** the question, selected device names, and retrieved public/fictional report excerpts are sent to OpenAI only after the checkbox and research button. API requests set `store=False`; that is not a claim of zero provider retention. No local database persists uploads or answers. Streamlit session state survives normal interactions but not necessarily a refresh or server restart. No API-key-free AI simulation is presented as a real integration.

**Deliberately deferred:** raw MAUDE ingestion, live FDA search, user accounts, permanent storage, review submission, ratings, sales connections, email, clinical advice, and production deployment.

## Run checks

With the virtual environment active and packages installed, stop the server or open a second terminal in `device-insight` and run:

```bash
source .venv/bin/activate
python -m unittest -v test_core.py test_ui.py test_api_config.py
```

These checks use real scikit-learn locally; agent dispatch is tested with scripted API responses, without spending credits. A successful live LLM request must still be demonstrated with your own API key. Dependency ranges permit current compatible releases; for repeatable submission, after successful installation run `python -m pip freeze > requirements-lock.txt` and keep that lock file with your project.

## Documentation used

- OpenAI quickstart: https://developers.openai.com/api/docs/quickstart
- OpenAI function calling: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI Responses reference: https://developers.openai.com/api/reference/resources/responses/methods/create
- Streamlit state: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- TF-IDF: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
- K-Means: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html
