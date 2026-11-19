# Medicare Provider Data Quality & Anomaly Analysis

**Author:** [Khagendra Adhikari](https://github.com/khagenA)

## Project Overview

I use Python to explore data quality, service volume, Medicare charges, and payment patterns in publicly available Medicare data. The notebook focuses on aggregate checks and straightforward summaries and visualizations.

## Dataset

The source is the CMS [Medicare Physician & Other Practitioners — by Provider and Service](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service) dataset for calendar year 2024. The local file contains a nonrandom Maryland sample of 5,000 rows and 567 distinct NPIs. It was copied from a previously acquired sample and is not included in Git.

Each source record summarizes one rendering provider × HCPCS code × place of service. I selected five blocks of 1,000 Maryland rows, sorted by rendering NPI, at offsets 0, 45,000, 90,000, 135,000, and 180,000. The previously verified Maryland-filtered row count was 228,520. I excluded HCPCS/CPT codes and descriptions from the downloaded sample as a licensing precaution; code-specific comparisons are therefore unavailable.

## Tools

- Python, pandas, NumPy, and matplotlib
- JupyterLab / Jupyter Notebook

## Methodology

I load and inspect the data, check missing and negative values, confirm state consistency and numeric types, and count projected duplicate rows. I calculate descriptive statistics for service volume and payment measures, create two histograms, and apply the global 1.5×IQR rule to `Avg_Mdcr_Pymt_Amt`. I do not remove or change flagged observations.

## Data Acquisition

Run `python download_data.py` from the project root to obtain the sample through the CMS public API. The script requests only the approved columns, checks the Maryland-filtered row count against 228,520, and refuses to overwrite an existing `data/cms_md_2024_sample.csv`. Raw data is excluded from Git. This sampling procedure is repeatable, but exact future records are not guaranteed if CMS updates the data or ordering among tied NPI values changes.

The existing local CSV is already present in this workspace, so the downloader will stop safely. To reacquire it, start from a fresh clone or safely back up the existing CSV outside `data/` before removing it yourself.

## Key Findings

- 5,000 rows and 567 distinct NPIs.
- Zero missing values and zero negative values in the checked numeric measures.
- Three projected duplicate rows; these are not confirmed source duplicates because HCPCS fields were excluded.
- Median `Tot_Srvcs`: 49 services per record.
- Median `Avg_Mdcr_Pymt_Amt`: $57.45 per service record.
- Payment Q1: $22.33; Q3: $97.43; IQR: $75.10.
- Payment IQR fences: −$90.31 (lower) and $210.07 (upper).
- The global rule flagged 279 high and 0 low payment values: 279 of 5,000 rows (5.58%).

## Visualizations

- [Service volume histogram](figures/service_volume.png)
- [Average Medicare payment histogram](figures/payment_distribution.png)
- [Payment IQR boxplot](figures/payment_iqr.png)

## Setup and Reproducibility

A fresh clone does not contain the raw CSV. Run the downloader before launching the notebook. If the CSV already exists, the script stops rather than replacing it.

**Windows (PowerShell)** — run from the project root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python download_data.py
jupyter lab notebook/medicare_analysis.ipynb
```

**macOS or Linux** — run from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python download_data.py
jupyter lab notebook/medicare_analysis.ipynb
```

## Limitations

This nonrandom sample does not cover all providers. Records combine different service types and amounts, and without HCPCS fields I cannot compare procedure codes. CMS privacy suppression can remove low-beneficiary service records. The data are aggregated and do not support patient-level clinical risk adjustment or provider-level investigation. IQR flags are global and unadjusted across a mixed service population; they are not evidence of fraud, waste, abuse, or noncompliance.

CMS is the source of the underlying Medicare data; this independent project is not affiliated with or endorsed by CMS. CPT is copyrighted by the American Medical Association (AMA), and later reuse of CPT content may require a separate license. See the [AMA CPT licensing FAQ](https://www.ama-assn.org/practice-management/cpt/cpt-licensing-frequently-asked-questions-faqs).
