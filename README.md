# MAUDE device reporting dashboard

This project uses your uploaded summaries and recreates the main visuals from your Colab notebook. The data is already prepared; you do not need to run Colab before trying the dashboard.

## Run the dashboard

1. Extract the ZIP. Open the `maude_dashboard` folder.
2. Install Python 3.11 or 3.12 if needed. Open a terminal in this folder.
3. Install the app dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   python -m streamlit run app.py
   ```

5. The dashboard opens in your browser. Keep the terminal open while using it. On Windows, substitute `py` for `python` if that is your available command.

To host on Streamlit Community Cloud, put the contents of this folder in your GitHub repository, preserving the `data` and `.streamlit` folders. In Community Cloud, create an app, choose that repository and branch, and set the entrypoint to `app.py` (or its full repository-relative path). Review repository/app visibility before sharing. Nothing has been published by this delivery.

Official instructions: https://docs.streamlit.io/develop/concepts/architecture/run-your-app and https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Use the comparison

- The ten company pills independently turn on/off. Abbott, BD, and Medtronic start selected, with the five device trends used in your notebook.
- The searchable table beside the graph adds/removes individual company/device lines. The first 60 matches plus selected rows are displayed; search finds any category. A newly enabled company initially selects its largest category. Selections are retained when a company is turned off.
- Choose any subset of 2021–2025. Hover over a line for its full name, counts, denominator, and percentage.
- The default measure is **Share within company (%)**. You can switch to raw device-record counts or **Change since 2021** (2021 = 100).
- Download the current comparison as CSV. The Plotly toolbar also exports the chart as an image.
- Below the graph are device and company volume charts, a fixed outcome snapshot, qualitative themes with record references and counterexamples, a sensitivity comparison, and conclusions tied to your official project. The original A/B proposal is summarized without replacing it with a new experiment design.

## What normalization does

Your device CSV already contains `PERCENT_OF_COMPANY_YEAR`. It equals:

`100 × device-category records / all device records for that company and year`

The included preparation code verifies the original percentages, then recalculates them without the original four-decimal rounding. The denominator always includes all device categories, including unspecified labels, even when the chart shows only a few. A 20% value means one-fifth of that company's device records that year concerned that category.

This makes reporting composition comparable despite unequal record volumes. It does not adjust for how many devices each company sells or how often they are used. Companies have different product portfolios; a category's share can rise because another category fell. Do not interpret these values as device failure rates or company safety rankings.

The index is `100 × current-year count / that same company/device's 2021 count`. It measures relative change in record volume. The baseline stays 2021 even if that year is hidden. A missing or zero baseline produces a blank index, not an infinite value. Missing category/year rows remain gaps, not assumed zero counts. Removing a year leaves a gap in the line.

FDA guidance: https://open.fda.gov/data/maude/

## Colab preparation

Open `Prepare_MAUDE_for_Streamlit.ipynb` in Colab. Run its cells in order and upload one device-type summary CSV and the company/year CSV when prompted. The notebook validates totals, recalculates percentages, preserves raw counts, previews normalized trends, and downloads a ZIP of prepared data. Put the generated `device_trends.csv` and `company_year.csv` in this app's `data` folder, replacing those two files. Keep the narrative and outcome snapshot CSVs already in that folder.

If continuing in your original notebook, ensure the pandas import runs before its CSV-loading cell. The companion notebook has the imports in the correct order and does not require the missing outcomes CSV.

For local preparation:

```bash
python prepare_data.py --devices "path/to/device_summary.csv" --companies "path/to/company_year_summary.csv" --output data
```

## Source and validation notes

- The two uploaded device-type summaries are byte-identical. Only one was used.
- All 50 company/year groups reconcile exactly: 4,779,852 device records across ten companies and five year labels.
- All supplied device shares agree with the calculation to four-decimal rounding.
- There are 22 source rows with `NA` or `N/A` labels, containing 713 records. They are retained under `Unknown / not specified`. Two resulting same-category/year/company pairs are summed, reducing 19,406 source rows to 19,404 prepared rows. These are not treated as duplicate adverse events.
- Other category names are retained apart from surrounding whitespace. Similar names, misspellings, and clinical aliases are not automatically combined. Product-code mapping would be needed for reliable category harmonization.
- The unit is `DEVICE_RECORD_COUNT`. These summaries cannot establish counts of unique reports, patients, or incidents. Do not sum outcome entries and device records as though they were the same unit.
- The ten companies are the supplied study selection. An industry-wide “top ten” ranking is not established by these files.
- Year labels are 2021–2025. Extraction date, date-field basis (event date versus report receipt date), and full-year coverage have not been verified.
- `outcomes_notebook_snapshot.csv` is recovered from the complete seven-row table stored in cell 18 (zero-based) of the supplied notebook. The separate underlying outcomes CSV was not uploaded. Its values are preserved, including rounded percentages. It is a fixed historical snapshot with no company/year fields.
- The 30 narrative rows are supplied sample text, not verified quotations or a representative sample. Optional theme counts reproduce the notebook's substring rules; overlapping themes, negation, and broad keywords limit interpretation.
- The notebook's claims about causes of spikes (recalls, regulatory changes, adoption) were not established by the summaries and are not presented as findings in the dashboard.

## Verification status

Data reconciliation, percentage calculations, fixed-baseline indexing, missing-year gaps, filtering invariance, selection-state callback behavior, and Python syntax were checked. The Colab calculation and plotting cells were exercised locally using the supplied files.

Streamlit and Plotly could not be installed in the authoring environment. The live interface has not been launched or visually verified; the dependency file and run instructions are included for that final check.

## Files

- `app.py`: Streamlit interface.
- `chart_data.py`: trend preparation and gap handling.
- `prepare_data.py`: reproducible normalization and validation.
- `Prepare_MAUDE_for_Streamlit.ipynb`: Colab preparation walkthrough.
- `data/`: prepared input tables and validation/provenance notes.
- `requirements.txt` and `.streamlit/config.toml`: app dependencies and appearance.

## Dashboard assignment requirements applied

The attached official project labels the dashboard section as Section 4. This update implements the dashboard requirements you referred to, preserving the project argument and using normalized device records.

| Requirement | Implementation |
|---|---|
| Questions, evidence, conclusions understandable without notebook | Main question and conclusion at top; interpretation beside charts; Project conclusions tab |
| Key quantitative visuals | Normalized multi-line graph, device-category bars, company bars, labeled outcome snapshot |
| Useful qualitative summary | Context-coded theme chart, examples with MDR references, counterexamples, sample table |
| Meaningful interaction | Independent company On/Off selection, device checkboxes, years and measures |
| Selections, units, observation counts visible | Company/year widgets, metric labels, total counts, hover numerators/denominators, narrative sample count |
| Empty selections | Clear message for no companies, years, device trends, or narrative rows |
| Static findings clearly scoped | Whole-dataset concentration statement, unfiltered text examples, sensitivity table, and outcome snapshot explicitly labeled |
| Full-screen legibility | Wide page, graph beside searchable device table, supporting evidence in tabs |
| Layout sketch and revision explanation | figures/dashboard_revision_sketch.svg and notebook addendum below |
| Source, dependencies, opening instructions | app.py, chart_data.py, requirements.txt, data folder, and instructions above |

**Notebook addendum to copy into the existing official notebook:** The attached layout sketch was prepared before the assignment-driven dashboard revision; the baseline app already existed. The revision adds the main question/conclusion and a qualitative evidence tab with examples and counterexamples. This allows visitors to understand the argument without reading the notebook. Independent company buttons support cumulative comparison. The default percentage divides each category by all device records for the same company/year, and filtering does not change that denominator. Static findings explicitly identify their population. The qualitative annotations were assisted by ChatGPT/Codex and should be reviewed by the author.

The delivered ZIP updates the dashboard project. It does not replace the official project document or claim to complete presentation, portfolio, or hosting requirements.
