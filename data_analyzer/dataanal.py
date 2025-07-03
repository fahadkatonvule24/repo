import re
import os
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import logging
import sys
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.svm import OneClassSVM
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data_analyzer.log')
    ]
)
logger = logging.getLogger(__name__)

# Try to import TensorFlow but make it optional
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, TimeDistributed
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
    logger.info("TensorFlow is available")
except ImportError:
    TF_AVAILABLE = False
    logger.warning("TensorFlow is not available. LSTM Autoencoder will be disabled")

class AdvancedDataAnalyzer:
    def __init__(self, output_dir='analysis_results'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory: {os.path.abspath(output_dir)}")
        
    def detect_encoding(self, file_path):
        """Detect file encoding with fallback to UTF-8"""
        logger.info("Detecting file encoding...")
        try:
            # Try to import chardet if available
            import chardet
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read(10000))  # Only read first 10KB for speed
            encoding = result['encoding'] if result['encoding'] else 'utf-8'
            confidence = result['confidence']
            logger.info(f"Detected encoding: {encoding} with confidence {confidence:.2f}")
            return encoding
        except ImportError:
            logger.warning("chardet module not installed, using UTF-8 as default")
            return 'utf-8'
        except Exception as e:
            logger.error(f"Encoding detection failed: {str(e)}, using UTF-8")
            return 'utf-8'
    
    def load_data(self, file_path):
        """Load data from various file types with automatic detection"""
        file_path = Path(file_path)
        logger.info(f"Analyzing file: {file_path}")
        logger.info(f"File directory: {file_path.parent.absolute()}")
        logger.info(f"File size: {file_path.stat().st_size / (1024*1024):.2f} MB")
        
        encoding = self.detect_encoding(file_path)
        
        try:
            if file_path.suffix in ('.log', '.txt'):
                logger.info("File identified as log/text file")
                return self.parse_log_file(file_path, encoding)
            elif file_path.suffix == '.csv':
                logger.info("File identified as CSV")
                return pd.read_csv(file_path, encoding=encoding, on_bad_lines='skip', engine='python')
            elif file_path.suffix in ('.xls', '.xlsx'):
                logger.info("File identified as Excel")
                return pd.read_excel(file_path)
            elif file_path.suffix == '.json':
                logger.info("File identified as JSON")
                return pd.read_json(file_path)
            elif file_path.suffix == '.parquet':
                logger.info("File identified as Parquet")
                return pd.read_parquet(file_path)
            else:
                logger.warning("Unsupported file type, attempting to read as text")
                return self.parse_unknown_file(file_path, encoding)
        except Exception as e:
            logger.error(f"Error loading file: {str(e)}")
            raise
    
    def parse_unknown_file(self, file_path, encoding):
        """Parse unknown file types using heuristic methods"""
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                lines = f.readlines()
            
            # Attempt to detect structure
            if any(',' in line for line in lines[:10]):
                logger.info("Detected CSV-like structure")
                return pd.read_csv(file_path, encoding=encoding, on_bad_lines='skip', engine='python')
            elif any('\t' in line for line in lines[:10]):
                logger.info("Detected TSV structure")
                return pd.read_csv(file_path, sep='\t', encoding=encoding, on_bad_lines='skip', engine='python')
            else:
                logger.info("Treating as unstructured text")
                return pd.DataFrame({'text': lines})
        except Exception as e:
            logger.error(f"Error parsing unknown file: {str(e)}")
            return pd.DataFrame({'text': ['File parsing failed']})
    
    def parse_log_file(self, file_path, encoding):
        """Parse log files using flexible patterns"""
        logger.info("Parsing log file with flexible patterns...")
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                logs = f.readlines()
            
            # Common log patterns
            patterns = [
                # Apache/NGINX style
                r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+)\s*(?P<protocol>\S*)" (?P<status>\d+) (?P<size>\d+)',
                # Syslog style
                r'(?P<timestamp>\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) (?P<host>\S+) (?P<app>\S+): (?P<message>.*)',
                # Standard timestamp, IP, message
                r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [A-Z]{3}),(?P<ip>[\d\.a-fA-F:]+),(?P<message>.*)',
                # Simplified pattern
                r'(?P<timestamp>.+?),(?P<ip>.+?),(?P<message>.*)'
            ]
            
            parsed_logs = []
            parse_errors = 0
            pattern_used = None
            
            for pattern in patterns:
                try:
                    logger.info(f"Trying pattern: {pattern[:50]}...")
                    parsed_logs = []
                    parse_errors = 0
                    compiled = re.compile(pattern)
                    
                    for log in logs:
                        match = compiled.search(log.strip())
                        if match:
                            parsed_logs.append(match.groupdict())
                        else:
                            parse_errors += 1
                    
                    if parsed_logs:
                        pattern_used = pattern
                        logger.info(f"Pattern matched {len(parsed_logs)}/{len(logs)} lines")
                        break
                except Exception as e:
                    logger.error(f"Pattern failed: {str(e)}")
            
            if not parsed_logs:
                logger.warning("No patterns matched, returning raw logs")
                return pd.DataFrame({'raw': [log.strip() for log in logs]})
            
            df = pd.DataFrame(parsed_logs)
            logger.info(f"Parse errors: {parse_errors}/{len(logs)}")
            
            # Attempt timestamp conversion
            if 'timestamp' in df.columns:
                logger.info("Attempting timestamp conversion...")
                try:
                    # Try multiple datetime formats
                    for fmt in ('%Y-%m-%d %H:%M:%S %Z', '%d/%b/%Y:%H:%M:%S %z', '%b %d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                        try:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], format=fmt, errors='raise')
                            logger.info(f"Timestamp converted with format: {fmt}")
                            break
                        except:
                            continue
                    else:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                        logger.warning("Used coerce for timestamp conversion")
                except Exception as e:
                    logger.error(f"Timestamp conversion error: {str(e)}")
            
            return df
        except Exception as e:
            logger.error(f"Error parsing log file: {str(e)}")
            return pd.DataFrame({'raw': [f'Error parsing log: {str(e)}']})
    
    def preprocess_data(self, df):
        """Automated data preprocessing pipeline"""
        logger.info("Starting data preprocessing")
        
        if df.empty:
            logger.warning("Empty dataframe after loading")
            return df
        
        # Initial cleaning
        initial_count = len(df)
        df = df.dropna(thresh=len(df.columns)//2)  # Remove rows with >50% missing
        df = df.drop_duplicates()
        logger.info(f"Removed {initial_count - len(df)} rows (missing data/duplicates)")
        
        # Automated type detection and conversion
        for col in df.columns:
            # Skip if already datetime
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
                
            # Attempt datetime conversion
            if df[col].dtype == 'object':
                try:
                    df[col] = pd.to_datetime(df[col], errors='ignore')
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        logger.info(f"Converted column '{col}' to datetime")
                        continue
                except:
                    pass
            
            # Attempt numeric conversion
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
                if np.issubdtype(df[col].dtype, np.number):
                    logger.info(f"Converted column '{col}' to numeric")
                    continue
            except:
                pass
        
        # Text preprocessing
        text_cols = [col for col in df.columns if df[col].dtype == 'object']
        for col in text_cols:
            # Simple text cleaning
            df[col] = df[col].astype(str).str.strip().str.lower()
        
        # Feature engineering for datetime columns
        datetime_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
        for col in datetime_cols:
            df[f'{col}_year'] = df[col].dt.year
            df[f'{col}_month'] = df[col].dt.month
            df[f'{col}_day'] = df[col].dt.day
            df[f'{col}_hour'] = df[col].dt.hour
            df[f'{col}_dow'] = df[col].dt.dayofweek
            logger.info(f"Created time features for '{col}'")
        
        # Categorical encoding
        cat_cols = [col for col in df.columns if df[col].nunique() < 50 and df[col].dtype == 'object']
        for col in cat_cols:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            logger.info(f"Label encoded '{col}' with {df[col].nunique()} categories")
        
        # Text vectorization for important text columns
        text_cols = [col for col in df.columns if df[col].dtype == 'object' and df[col].nunique() > 50]
        for col in text_cols[:min(2, len(text_cols))]:  # Limit to top 2 text columns
            logger.info(f"Vectorizing text column: '{col}'")
            try:
                vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
                tfidf_matrix = vectorizer.fit_transform(df[col].fillna(''))
                tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), 
                                        columns=[f"{col}_tfidf_{i}" for i in range(tfidf_matrix.shape[1])])
                df = pd.concat([df, tfidf_df], axis=1)
                df.drop(col, axis=1, inplace=True)
            except Exception as e:
                logger.error(f"Text vectorization failed for column '{col}': {str(e)}")
        
        logger.info(f"Preprocessed data shape: {df.shape}")
        return df
    
    def detect_anomalies(self, df):
        """Advanced anomaly detection using multiple AI methods"""
        logger.info("Running anomaly detection")
        results = {}
        
        # Select numeric features
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        if not numeric_cols:
            logger.warning("No numeric columns for anomaly detection")
            return results
        
        X = df[numeric_cols].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Method 1: Isolation Forest
        logger.info("Running Isolation Forest...")
        iso_forest = IsolationForest(contamination=0.05, random_state=42)
        df['anomaly_score_iso'] = iso_forest.fit_predict(X_scaled)
        df['anomaly_iso'] = df['anomaly_score_iso'] == -1
        results['isolation_forest'] = df[df['anomaly_iso']].copy()
        
        # Method 2: One-Class SVM
        logger.info("Running One-Class SVM...")
        oc_svm = OneClassSVM(nu=0.05)
        df['anomaly_score_svm'] = oc_svm.fit_predict(X_scaled)
        df['anomaly_svm'] = df['anomaly_score_svm'] == -1
        results['oneclass_svm'] = df[df['anomaly_svm']].copy()
        
        # Method 3: DBSCAN Clustering
        logger.info("Running DBSCAN...")
        dbscan = DBSCAN(eps=0.5, min_samples=5)
        df['cluster_dbscan'] = dbscan.fit_predict(X_scaled)
        df['anomaly_dbscan'] = df['cluster_dbscan'] == -1
        results['dbscan'] = df[df['anomaly_dbscan']].copy()
        
        # Method 4: LSTM Autoencoder (for time series) - only if TensorFlow is available
        if TF_AVAILABLE:
            time_cols = [col for col in df.columns if 'timestamp' in col and pd.api.types.is_datetime64_any_dtype(df[col])]
            if time_cols and len(df) > 1000:
                try:
                    logger.info("Running LSTM Autoencoder...")
                    time_col = time_cols[0]
                    time_series = df.set_index(time_col).sort_index()
                    numeric_cols = time_series.select_dtypes(include=np.number).columns
                    
                    if len(numeric_cols) > 0:
                        # Create sequences for LSTM
                        sequence_length = 30
                        sequences = []
                        for i in range(len(time_series) - sequence_length):
                            sequences.append(time_series[numeric_cols].iloc[i:i+sequence_length].values)
                        
                        sequences = np.array(sequences)
                        
                        # Build autoencoder
                        model = Sequential()
                        model.add(LSTM(64, activation='relu', input_shape=(sequences.shape[1], sequences.shape[2]), 
                                      return_sequences=True))
                        model.add(LSTM(32, activation='relu', return_sequences=False))
                        model.add(RepeatVector(sequences.shape[1]))
                        model.add(LSTM(32, activation='relu', return_sequences=True))
                        model.add(LSTM(64, activation='relu', return_sequences=True))
                        model.add(TimeDistributed(Dense(sequences.shape[2])))
                        
                        model.compile(optimizer='adam', loss='mse')
                        early_stop = EarlyStopping(monitor='val_loss', patience=2, verbose=0)
                        
                        # Train-test split
                        train_size = int(len(sequences) * 0.8)
                        model.fit(sequences[:train_size], sequences[:train_size], 
                                  epochs=10, batch_size=32, 
                                  validation_split=0.1, callbacks=[early_stop],
                                  verbose=0)
                        
                        # Calculate reconstruction error
                        reconstructions = model.predict(sequences)
                        mse = np.mean(np.power(sequences - reconstructions, 2), axis=(1, 2))
                        df['reconstruction_error'] = np.nan
                        df.iloc[sequence_length:, df.columns.get_loc('reconstruction_error')] = mse
                        
                        # Detect anomalies based on reconstruction error
                        threshold = np.quantile(mse, 0.95)
                        df['anomaly_lstm'] = df['reconstruction_error'] > threshold
                        results['lstm_autoencoder'] = df[df['anomaly_lstm']].copy()
                except Exception as e:
                    logger.error(f"LSTM Autoencoder failed: {str(e)}")
        else:
            logger.info("Skipping LSTM Autoencoder because TensorFlow is not available")
        
        return results
    
    def time_series_analysis(self, df):
        """Comprehensive time series analysis and forecasting"""
        logger.info("Performing time series analysis")
        results = {}
        
        # Find datetime columns
        datetime_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
        if not datetime_cols:
            logger.warning("No datetime columns found for time series analysis")
            return results
        
        time_col = datetime_cols[0]
        df_ts = df.set_index(time_col).sort_index()
        
        # Find numeric target columns
        numeric_cols = df_ts.select_dtypes(include=np.number).columns
        if not numeric_cols:
            logger.warning("No numeric columns found for time series analysis")
            return results
        
        for target_col in numeric_cols[:min(2, len(numeric_cols))]:  # Limit to first 2 numeric columns
            ts_data = df_ts[target_col].dropna()
            if len(ts_data) < 100:
                logger.info(f"Not enough data ({len(ts_data)} points) for {target_col} time series")
                continue
            
            logger.info(f"Analyzing time series: {target_col}")
            
            # Stationarity test
            adf_result = adfuller(ts_data)
            is_stationary = adf_result[1] < 0.05
            logger.info(f"Stationary: {is_stationary} (p-value={adf_result[1]:.4f})")
            
            # Time series decomposition
            try:
                period = min(30, len(ts_data)//2)
                decomposition = seasonal_decompose(ts_data, period=period, model='additive')
                plt.figure(figsize=(12, 8))
                decomposition.plot()
                plt.suptitle(f'Decomposition of {target_col}')
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, f'decomposition_{target_col}.png'))
                plt.close()
                logger.info(f"Created decomposition plot for {target_col}")
            except Exception as e:
                logger.warning(f"Decomposition failed for {target_col}: {str(e)}")
            
            # Facebook Prophet forecasting
            try:
                logger.info("Running Prophet forecasting...")
                prophet_df = pd.DataFrame({
                    'ds': ts_data.index,
                    'y': ts_data.values
                }).dropna()
                
                model = Prophet(seasonality_mode='multiplicative', daily_seasonality=True)
                model.fit(prophet_df)
                
                future = model.make_future_dataframe(periods=30)
                forecast = model.predict(future)
                
                fig = model.plot(forecast)
                plt.title(f'Prophet Forecast for {target_col}')
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, f'prophet_forecast_{target_col}.png'))
                plt.close()
                
                fig2 = model.plot_components(forecast)
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, f'prophet_components_{target_col}.png'))
                plt.close()
                
                results[target_col] = {
                    'forecast': forecast,
                    'model': model,
                    'is_stationary': is_stationary
                }
            except Exception as e:
                logger.error(f"Prophet forecasting failed for {target_col}: {str(e)}")
        
        return results
    
    def cluster_analysis(self, df):
        """Advanced clustering for pattern discovery"""
        logger.info("Performing cluster analysis")
        
        if df.empty:
            logger.warning("Skipping clustering for empty dataframe")
            return None
            
        # Select numeric features
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        if len(numeric_cols) < 2:
            logger.warning("Not enough numeric columns for clustering")
            return None
        
        X = df[numeric_cols].fillna(0)
        if len(X) > 10000:
            X = X.sample(10000, random_state=42)
            logger.info("Sampled 10,000 rows for clustering")
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Dimensionality reduction for visualization
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        df['pca1'] = X_pca[:, 0]
        df['pca2'] = X_pca[:, 1]
        
        # KMeans clustering
        logger.info("Running KMeans clustering...")
        kmeans = KMeans(n_clusters=min(5, len(X)//10), random_state=42)
        df['cluster_kmeans'] = kmeans.fit_predict(X_scaled)
        
        # DBSCAN clustering
        logger.info("Running DBSCAN clustering...")
        dbscan = DBSCAN(eps=0.5, min_samples=5)
        df['cluster_dbscan'] = dbscan.fit_predict(X_scaled)
        
        # Visualization
        plt.figure(figsize=(15, 6))
        
        plt.subplot(121)
        sns.scatterplot(data=df, x='pca1', y='pca2', hue='cluster_kmeans', palette='viridis')
        plt.title('KMeans Clustering')
        
        plt.subplot(122)
        sns.scatterplot(data=df, x='pca1', y='pca2', hue='cluster_dbscan', palette='viridis')
        plt.title('DBSCAN Clustering')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'clustering.png'))
        plt.close()
        logger.info("Saved clustering visualization")
        
        return df
    
    def analyze_log_specific(self, df):
        """Advanced security analysis for log files"""
        logger.info("Performing security log analysis")
        results = {}
        
        # Check if this looks like a security log
        if 'message' not in df.columns:
            return results
        
        # Failed login detection
        failed_login_keywords = ['fail', 'invalid', 'denied', 'refused', 'unauthorized', 'error']
        df['failed_login'] = df['message'].str.lower().str.contains('|'.join(failed_login_keywords))
        
        if 'failed_login' in df.columns:
            # IP frequency analysis
            if 'ip' in df.columns:
                ip_freq = df['ip'].value_counts().reset_index()
                ip_freq.columns = ['ip', 'count']
                
                # Suspicious IPs with high failure rates
                failures_by_ip = df[df['failed_login']].groupby('ip').size().reset_index()
                failures_by_ip.columns = ['ip', 'failures']
                
                ip_stats = pd.merge(ip_freq, failures_by_ip, on='ip', how='left').fillna(0)
                ip_stats['failure_rate'] = ip_stats['failures'] / ip_stats['count']
                
                # Identify suspicious IPs
                suspicious_ips = ip_stats[ip_stats['failure_rate'] > 0.5]
                results['suspicious_ips'] = suspicious_ips
                logger.info(f"Found {len(suspicious_ips)} suspicious IPs")
            
            # Time-based anomaly detection
            time_cols = [col for col in df.columns if 'timestamp' in col and pd.api.types.is_datetime64_any_dtype(df[col])]
            if time_cols:
                time_col = time_cols[0]
                df.set_index(time_col, inplace=True)
                failures_over_time = df['failed_login'].resample('1H').sum().fillna(0)
                
                # Detect spikes in failures
                mean_failures = failures_over_time.mean()
                std_failures = failures_over_time.std()
                spike_threshold = mean_failures + 3 * std_failures
                failure_spikes = failures_over_time[failures_over_time > spike_threshold]
                
                results['failure_spikes'] = failure_spikes
                logger.info(f"Found {len(failure_spikes)} failure spikes")
                
                # Visualize
                plt.figure(figsize=(12, 6))
                failures_over_time.plot(label='Hourly Failures')
                plt.axhline(y=spike_threshold, color='r', linestyle='--', label='Spike Threshold')
                plt.title('Failed Logins Over Time')
                plt.xlabel('Timestamp')
                plt.ylabel('Failed Logins')
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(self.output_dir, 'failed_logins_over_time.png'))
                plt.close()
        
        return results
    
    def generate_report(self, df, anomalies, ts_results, clusters, log_results):
        """Generate comprehensive HTML report"""
        logger.info("Generating final report")
        
        report_path = os.path.join(self.output_dir, 'analysis_report.html')
        with open(report_path, 'w') as f:
            f.write("""
            <html>
            <head>
                <title>Advanced Data Analysis Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    h1, h2, h3 { color: #2c3e50; }
                    .section { margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 20px; }
                    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                    th { background-color: #3498db; color: white; }
                    tr:nth-child(even) { background-color: #f2f2f2; }
                    img { max-width: 100%; margin: 10px 0; border: 1px solid #ddd; }
                    .summary-card { 
                        background: #f8f9fa; 
                        border-left: 4px solid #3498db; 
                        padding: 15px; 
                        margin: 15px 0; 
                    }
                </style>
            </head>
            <body>
                <h1>Advanced Data Analysis Report</h1>
            """)
            
            # Dataset overview
            f.write("<div class='section'><h2>Dataset Overview</h2>")
            f.write(f"<p><strong>Total Rows:</strong> {len(df):,}</p>")
            f.write(f"<p><strong>Total Columns:</strong> {len(df.columns)}</p>")
            f.write(f"<p><strong>Memory Usage:</strong> {df.memory_usage(deep=True).sum() / (1024**2):.2f} MB</p>")
            
            # Data types
            f.write("<h3>Data Types</h3>")
            dtype_counts = df.dtypes.value_counts().reset_index()
            dtype_counts.columns = ['Data Type', 'Count']
            f.write(dtype_counts.to_html(index=False))
            
            # Missing values
            f.write("<h3>Missing Values</h3>")
            missing = df.isnull().sum().reset_index()
            missing.columns = ['Column', 'Missing Count']
            missing['Missing %'] = (missing['Missing Count'] / len(df)) * 100
            f.write(missing.to_html(index=False))
            f.write("</div>")
            
            # Anomaly detection results
            if anomalies:
                f.write("<div class='section'><h2>Anomaly Detection</h2>")
                for method, anomaly_df in anomalies.items():
                    f.write(f"<div class='summary-card'>")
                    f.write(f"<h3>{method.replace('_', ' ').title()} Anomalies</h3>")
                    f.write(f"<p>Detected: {len(anomaly_df)} anomalies ({len(anomaly_df)/len(df)*100:.2f}%)</p>")
                    if not anomaly_df.empty:
                        f.write(anomaly_df.head(10).to_html(index=False))
                    f.write("</div>")
                f.write("</div>")
            
            # Time series results
            if ts_results:
                f.write("<div class='section'><h2>Time Series Analysis</h2>")
                for target, result in ts_results.items():
                    f.write(f"<div class='summary-card'>")
                    f.write(f"<h3>{target} Analysis</h3>")
                    f.write(f"<p>Stationary: {result['is_stationary']}</p>")
                    if 'forecast' in result:
                        f.write("<h4>Forecast Preview</h4>")
                        f.write(result['forecast'][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail().to_html(index=False))
                        f.write(f"<h4>Forecast Visualization</h4>")
                        f.write(f"<img src='prophet_forecast_{target}.png' alt='{target} forecast'>")
                        f.write(f"<h4>Components Visualization</h4>")
                        f.write(f"<img src='prophet_components_{target}.png' alt='{target} components'>")
                    f.write("</div>")
                f.write("</div>")
            
            # Clustering results
            if clusters is not None and 'cluster_kmeans' in clusters.columns:
                f.write("<div class='section'><h2>Cluster Analysis</h2>")
                cluster_counts = clusters['cluster_kmeans'].value_counts().reset_index()
                cluster_counts.columns = ['Cluster', 'Count']
                f.write(cluster_counts.to_html(index=False))
                f.write("<h3>Cluster Visualization</h3>")
                f.write("<img src='clustering.png' alt='Clustering results'>")
                f.write("</div>")
            
            # Log-specific results
            if log_results:
                f.write("<div class='section'><h2>Security Analysis</h2>")
                
                if 'suspicious_ips' in log_results:
                    f.write("<div class='summary-card'>")
                    f.write("<h3>Suspicious IPs</h3>")
                    f.write(f"<p>Found: {len(log_results['suspicious_ips'])} IPs with high failure rates</p>")
                    f.write(log_results['suspicious_ips'].to_html(index=False))
                    f.write("</div>")
                
                if 'failure_spikes' in log_results:
                    f.write("<div class='summary-card'>")
                    f.write("<h3>Failure Spikes</h3>")
                    f.write(f"<p>Detected: {len(log_results['failure_spikes'])} spikes in failed logins</p>")
                    f.write(log_results['failure_spikes'].reset_index().to_html(index=False))
                    f.write("<h3>Failure Pattern Visualization</h3>")
                    f.write("<img src='failed_logins_over_time.png' alt='Failed logins over time'>")
                    f.write("</div>")
                
                f.write("</div>")
            
            f.write("</body></html>")
        
        logger.info(f"Report generated: {os.path.abspath(report_path)}")
        return report_path
    
    def analyze(self, file_path):
        """Main analysis pipeline"""
        try:
            # Load and preprocess data
            df = self.load_data(file_path)
            df = self.preprocess_data(df)
            
            # Save cleaned data
            cleaned_path = os.path.join(self.output_dir, 'cleaned_data.csv')
            df.to_csv(cleaned_path, index=False)
            logger.info(f"Saved cleaned data: {cleaned_path}")
            
            # Initialize results
            anomalies = {}
            ts_results = {}
            clusters = None
            log_results = {}
            
            # Perform analyses
            if not df.empty:
                anomalies = self.detect_anomalies(df)
                ts_results = self.time_series_analysis(df)
                clusters = self.cluster_analysis(df)
                
                # Check if this is a log file
                if 'message' in df.columns or 'source' in df.columns:
                    log_results = self.analyze_log_specific(df)
            
            # Generate final report
            report_path = self.generate_report(df, anomalies, ts_results, clusters, log_results)
            
            return {
                'status': 'success',
                'report': report_path,
                'cleaned_data': cleaned_path,
                'anomalies': {k: len(v) for k, v in anomalies.items()},
                'time_series': list(ts_results.keys()),
                'clusters': clusters['cluster_kmeans'].nunique() if clusters is not None else 0
            }
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

def main():
    parser = argparse.ArgumentParser(
        description='Advanced AI-Powered Data Analyzer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('file_path', help='Path to the data file to analyze')
    parser.add_argument('--output', help='Output directory', default='analysis_results')
    args = parser.parse_args()
    
    print(f"\n{'='*50}")
    print(f"Advanced AI Data Analyzer")
    print(f"{'='*50}")
    print(f"Input file: {os.path.abspath(args.file_path)}")
    print(f"Output directory: {os.path.abspath(args.output)}")
    print(f"{'='*50}\n")
    
    analyzer = AdvancedDataAnalyzer(output_dir=args.output)
    result = analyzer.analyze(args.file_path)
    
    print("\nAnalysis Summary:")
    print(json.dumps(result, indent=2))
    
    if result['status'] == 'success':
        print("\nAnalysis completed successfully!")
        print(f"View report at: {result['report']}")
    else:
        print("\nAnalysis failed with error:")
        print(result['message'])

if __name__ == "__main__":
    import json
    main()