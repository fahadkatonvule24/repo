# Advanced AI‑Powered Data Analyzer

A batteries‑included data analysis CLI that loads diverse file types, preprocesses columns (typing, encoding, text cleanup), runs anomaly detection (Isolation Forest, One‑Class SVM, DBSCAN, optional LSTM autoencoder), performs time‑series analysis/Prophet forecasting, clustering with PCA visualization, and emits a rich HTML report plus cleaned CSV.

## Highlights
- **Auto file loading**: CSV, Excel, JSON, Parquet, logs/text with heuristics and encoding detection (uses `chardet` if available).
- **Preprocessing**: type inference, datetime/numeric conversion, missing/dupe handling, label encoding, limited TF‑IDF for large text columns, time features.
- **Anomaly Detection**: IsolationForest, One‑Class SVM, DBSCAN. Optional **LSTM Autoencoder** if TensorFlow is installed and the data is long enough.
- **Time Series**: ADF stationarity test, seasonal decomposition plots, Prophet forecast & components.
- **Clustering**: PCA to 2D, KMeans + DBSCAN with saved scatter plots.
- **Security log extras**: failed login heuristics, suspicious IPs, hourly failure spikes & chart.
- **Outputs**: `analysis_results/cleaned_data.csv`, `analysis_results/analysis_report.html`, plus PNG charts.

## Requirements
Python 3.9+ recommended. Install dependencies (some are optional but recommended):

```bash
pip install pandas numpy matplotlib seaborn scikit-learn statsmodels prophet chardet
# Optional for LSTM autoencoder:
pip install tensorflow
```

> **Tip:** `prophet` may require a C++ build toolchain; on some systems it’s packaged as `prophet` (PyPI) or `cmdstanpy` backend variants.

## Usage

```bash
python dataanal.py path/to/data.csv --output analysis_results
```

### Generated artifacts
- `analysis_results/cleaned_data.csv`
- `analysis_results/analysis_report.html`
- `analysis_results/clustering.png`
- `analysis_results/prophet_forecast_<col>.png`
- `analysis_results/prophet_components_<col>.png`
- `analysis_results/failed_logins_over_time.png` (if applicable)

## CLI
```
positional arguments:
  file_path            Path to the data file to analyze

optional arguments:
  --output OUTPUT      Output directory (default: analysis_results)
```

## Notes & Caveats
- **Large data**: For clustering, the script samples to 10,000 rows for performance.
- **Log parsing**: Tries several regexes; falls back to raw lines when no pattern fits.
- **Text vectorization**: Limits TF‑IDF to up to 2 text columns and 100 features each to bound memory.
- **TensorFlow optional**: LSTM autoencoder runs only when TF is installed and there’s enough sequential data.
- **Minor fix**: If you enable the LSTM autoencoder, add the missing import:
  ```python
  from tensorflow.keras.layers import RepeatVector
  ```

## License
Add your preferred license.
