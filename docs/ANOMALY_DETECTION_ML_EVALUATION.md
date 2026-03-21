# Anomaly Detection ML Evaluation Report
**Analysis Date:** 2026-03-15
**Analyst:** AI Engineer Agent
**Project:** Fazri Analyzer - Campus Security & Entity Tracking System
**Focus:** Should Rule-Based Anomaly Detection be Replaced/Augmented with ML?

---

## Executive Summary

**RECOMMENDATION: HYBRID APPROACH - Keep Rules + Add Unsupervised ML**

After analyzing the current rule-based anomaly detection system (19 distinct anomaly types across system and entity levels), I recommend a **phased hybrid approach** rather than full replacement:

### Phase 1 (Months 1-3): Keep All Rules + Add Unsupervised ML
- **Retain:** All 19 rule-based detectors (they provide high-precision, interpretable alerts)
- **Add:** Isolation Forest for discovering **unknown anomaly patterns** missed by rules
- **Rationale:** No labeled anomaly data exists; rules already cover well-defined security violations

### Phase 2 (Months 4-6): Time-Series Anomaly Detection
- **Add:** LSTM Autoencoder for temporal pattern anomalies (occupancy spikes, unusual access patterns)
- **Use Case:** Detect gradual behavioral shifts that rules cannot catch

### Phase 3 (Months 7+): Supervised Learning (if labels become available)
- **Conditional:** Only if security team labels historical anomalies as true/false positives
- **Algorithm:** XGBoost classifier to reduce false positives and prioritize alerts by risk

### Key Findings
- ✅ **No labeled anomaly data available** → Unsupervised/semi-supervised methods required
- ✅ **Rules are interpretable** → Critical for campus security explanations
- ✅ **~32,000 card swipe records + WiFi logs** → Sufficient data for ML training
- ⚠️ **Unknown false positive rate** → Need monitoring to validate rule effectiveness
- ⚠️ **Rules miss novel patterns** → ML can discover new anomaly types

---

## 1. Current System Analysis

### 1.1 System-Level Anomalies (Rule-Based)
**File:** `/Users/dinokage/dev/fazri-analyzer/backend/services/anomaly_detection.py`

| Anomaly Type | Detection Method | Threshold | Severity |
|--------------|------------------|-----------|----------|
| Overcrowding | Occupancy > Zone Capacity | Per-zone capacity | CRITICAL/HIGH |
| Underutilization | Occupancy < 20% capacity | Peak hours, >5 data points | LOW/MEDIUM |
| Data Integrity | Null timestamps, negative occupancy | N/A | MEDIUM/HIGH |
| Negative Flow | Exits > Entries by >5 | Per hour | HIGH |

**Strengths:**
- Simple, fast, deterministic
- 100% interpretable for security teams
- No training data required
- Low computational cost

**Weaknesses:**
- Fixed thresholds may not adapt to changing patterns
- Cannot detect complex multi-variate anomalies
- Miss novel attack vectors or behavioral drift

---

### 1.2 Entity-Level Anomalies (Rule-Based)
**File:** `/Users/dinokage/dev/fazri-analyzer/backend/services/entity_anomaly_detection.py`

**12 Anomaly Types:**
1. **Off-Hours Access** - Access outside zone operating hours (7am-9pm labs, etc.)
2. **Role Violations** - Students accessing faculty-only rooms (ROOM_A1, ROOM_A2)
3. **Department Violations** - Non-ECE/EEE students in LAB_305
4. **Impossible Travel** - OUT from Zone A → IN to Zone B in <2 minutes
5. **Location Mismatches** - Card swipe location ≠ WiFi location within 5 min
6. **Curfew Violations** - Hostel entry/exit after 23:00
7. **Excessive Access** - >10 swipes/hour in same zone
8. **Booking No-Shows** - Booked but never accessed during booking window
9. **Entry Without Exit** - IN swipe with no matching OUT (tailgating detection)
10. **Exit Without Entry** - OUT swipe with no prior IN (piggybacking detection)
11. **Abnormal Dwell Time** - Time in zone exceeds zone-specific max (e.g., 8h for labs)
12. **Consecutive Same Direction** - IN-IN or OUT-OUT swipes <2h apart (card sharing)

**Strengths:**
- Comprehensive security coverage
- Domain expert knowledge encoded
- Direction-aware (IN/OUT) for high precision
- Zone-specific customization

**Weaknesses:**
- Binary logic cannot handle nuanced cases
- No learning from historical patterns
- Threshold tuning requires manual adjustment
- Cannot detect slowly evolving attack patterns

---

## 2. Data Availability Assessment

### 2.1 Available Data for ML Training
**Location:** `/Users/dinokage/dev/fazri-analyzer/backend/augmented/`

| Data Source | Records | Features | Labeled? |
|-------------|---------|----------|----------|
| Card Swipes | ~32,456 | card_id, location, timestamp, IN/OUT | ❌ No |
| WiFi Logs | ~32,690 | MAC, location, timestamp, connection duration | ❌ No |
| Lab Bookings | Available | entity_id, room, start/end time | ❌ No |
| CCTV Frames | Available | frame_id, location, timestamp, persons_detected | ❌ No |

**Critical Gap:** **NO LABELED ANOMALY DATA**
- No historical "true positive" vs "false positive" labels
- No ground truth for supervised learning
- Security team has not validated past anomalies

**Implications:**
- ❌ Cannot train supervised classifiers (XGBoost, Random Forest)
- ✅ Can use unsupervised methods (Isolation Forest, Autoencoders)
- ✅ Can use semi-supervised methods (One-Class SVM)

### 2.2 Data Quality for ML
**Sufficient Volume:**
- ✅ 32,000+ records sufficient for unsupervised anomaly detection
- ✅ Multi-modal data (card + WiFi + booking) enables rich feature engineering
- ✅ Temporal data supports time-series models

**Data Challenges:**
- ⚠️ No entity demographic data for fairness testing (role/department only)
- ⚠️ Unknown data quality issues (missing swipes, sensor errors)
- ⚠️ No baseline "normal behavior" definition

---

## 3. ML Algorithm Evaluation

### 3.1 Supervised Anomaly Detection ❌ NOT VIABLE (No Labels)

**Algorithm:** XGBoost / Random Forest Classifier

**Requirements:**
- ✅ Sufficient data volume (32K+ records)
- ❌ **CRITICAL BLOCKER:** No labeled training data
- ❌ No validated anomalies (true/false positives)

**If Labels Become Available (Future Phase):**
```python
# Example: XGBoost for anomaly classification
from xgboost import XGBClassifier

features = [
    'hour', 'day_of_week', 'is_weekend',
    'time_since_last_access', 'access_frequency_1h',
    'prev_location_encoded', 'zone_risk_score',
    'role_encoded', 'department_encoded'
]

model = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=10  # Handle class imbalance (anomalies are rare)
)

model.fit(X_train, y_train)  # y_train = 0 (normal) or 1 (anomaly)
```

**Pros:**
- High accuracy if labeled data available (85-95% typical)
- Can learn complex patterns (multi-feature interactions)
- Feature importance for interpretability

**Cons:**
- **Requires 500-1000+ labeled anomalies** for training
- Cannot detect unknown anomaly types (only learns from labeled examples)
- Maintenance overhead (retraining as new anomalies emerge)

**Verdict:** ❌ **NOT RECOMMENDED** until anomaly labeling project completed

---

### 3.2 Unsupervised Anomaly Detection ✅ RECOMMENDED (Phase 1)

#### Option A: Isolation Forest (PRIMARY RECOMMENDATION)

**Algorithm:** Isolation Forest (sklearn)

**Why It Fits:**
- ✅ No labeled data required
- ✅ Fast training and inference (<10ms per prediction)
- ✅ Handles high-dimensional data well
- ✅ Detects **point anomalies** (unusual individual events)
- ✅ Works well with imbalanced data (anomalies are rare)

**Implementation:**
```python
from sklearn.ensemble import IsolationForest
import pandas as pd

# Feature engineering
features = pd.DataFrame({
    'hour': card_swipes['timestamp'].dt.hour,
    'day_of_week': card_swipes['timestamp'].dt.dayofweek,
    'is_weekend': card_swipes['timestamp'].dt.dayofweek >= 5,
    'time_since_last_access_hours': time_diffs,
    'access_frequency_last_hour': rolling_counts,
    'zone_encoded': label_encoder.fit_transform(card_swipes['location']),
    'direction_encoded': (card_swipes['IN_OUT'] == 'IN').astype(int),
    'hour_sin': np.sin(2 * np.pi * hour / 24),  # Cyclic encoding
    'hour_cos': np.cos(2 * np.pi * hour / 24),
})

# Train Isolation Forest
iso_forest = IsolationForest(
    n_estimators=200,        # Number of trees
    contamination=0.05,      # Expected anomaly rate (5%)
    max_samples=256,         # Subsample size
    random_state=42,
    n_jobs=-1                # Parallel processing
)

iso_forest.fit(features)

# Predict anomalies (-1 = anomaly, 1 = normal)
predictions = iso_forest.predict(features)
anomaly_scores = iso_forest.score_samples(features)  # Lower = more anomalous

# Extract anomalies
anomalies = card_swipes[predictions == -1].copy()
anomalies['anomaly_score'] = anomaly_scores[predictions == -1]
```

**Expected Performance:**
- **Precision:** 20-40% (many false positives expected - requires tuning)
- **Recall:** 60-80% (captures most true anomalies)
- **False Positive Rate:** 5-10% (tunable via contamination parameter)
- **Inference Latency:** <10ms per prediction

**Tuning Strategy:**
1. Start with `contamination=0.05` (assume 5% of data is anomalous)
2. Security team reviews flagged anomalies for 1-2 weeks
3. Adjust contamination based on false positive rate
4. Add feature engineering (location proximity, role-based features)

**Pros:**
- Discovers **unknown anomaly types** rules cannot catch
- No labeling required
- Fast training (<1 min on 32K records)
- Explainable (provides anomaly score ranking)

**Cons:**
- High false positive rate initially (requires tuning)
- Cannot explain *why* something is anomalous (black box scores)
- May flag legitimate edge cases as anomalies

**Verdict:** ✅ **RECOMMENDED for Phase 1** (complement to rules)

---

#### Option B: One-Class SVM

**Algorithm:** One-Class Support Vector Machine

**Why It Might Fit:**
- ✅ No labeled data required
- ✅ Learns decision boundary around "normal" behavior
- ✅ Good for low-dimensional data (<20 features)

**Implementation:**
```python
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

# Feature scaling required for SVM
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)

# Train One-Class SVM
oc_svm = OneClassSVM(
    kernel='rbf',      # Radial basis function
    gamma='auto',      # Auto-tune gamma
    nu=0.05            # Upper bound on anomaly rate (5%)
)

oc_svm.fit(features_scaled)
predictions = oc_svm.predict(features_scaled)
```

**Pros:**
- Works well for dense clusters of normal behavior
- Theoretically sound decision boundary
- Good for smooth, continuous features

**Cons:**
- ❌ **Slow training** on large datasets (>10K records)
- ❌ Not interpretable (no feature importance)
- ❌ Sensitive to feature scaling
- ❌ Hyperparameter tuning difficult (gamma, nu)

**Expected Performance:**
- **Precision:** 15-30% (high false positives)
- **Recall:** 50-70%
- **Training Time:** 5-10 minutes (vs <1 min for Isolation Forest)

**Verdict:** ❌ **NOT RECOMMENDED** (Isolation Forest is faster and more effective)

---

#### Option C: Local Outlier Factor (LOF)

**Algorithm:** Local Outlier Factor (sklearn)

**Why It Might Fit:**
- ✅ Detects local density-based anomalies
- ✅ Good for datasets with varying density regions
- ✅ No training phase (instance-based learning)

**Implementation:**
```python
from sklearn.neighbors import LocalOutlierFactor

lof = LocalOutlierFactor(
    n_neighbors=20,      # Number of neighbors to consider
    contamination=0.05,  # Expected anomaly rate
    novelty=False        # Fit + predict on same dataset
)

predictions = lof.fit_predict(features)
anomaly_scores = lof.negative_outlier_factor_
```

**Pros:**
- No training required (lazy learning)
- Detects local anomalies in non-uniform data
- Works well for spatial/temporal clusters

**Cons:**
- ❌ **Slow inference** (O(n) for each prediction - needs to compare to all training data)
- ❌ Not suitable for real-time detection on large datasets
- ❌ High memory usage (stores entire training set)

**Expected Performance:**
- **Precision:** 25-40%
- **Recall:** 60-80%
- **Inference Latency:** 100-500ms (too slow for real-time)

**Verdict:** ❌ **NOT RECOMMENDED** (too slow for production)

---

### 3.3 Time-Series Anomaly Detection ✅ RECOMMENDED (Phase 2)

#### Option A: LSTM Autoencoder (PRIMARY RECOMMENDATION)

**Algorithm:** Long Short-Term Memory (LSTM) Autoencoder

**Why It Fits:**
- ✅ Detects **temporal anomalies** (unusual sequences)
- ✅ Learns normal access patterns over time
- ✅ Can detect gradual behavioral drift
- ✅ Works well with sequential card swipe data

**Use Cases:**
- Detect sudden spike in zone occupancy (not just threshold violation)
- Unusual access time sequences (e.g., lab → hostel → lab within 10 min)
- Gradual behavioral changes (normal 9am user starts accessing at 2am)

**Implementation:**
```python
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import LSTM, Dense, RepeatVector, TimeDistributed

# Prepare sequential data (e.g., last 10 access events per entity)
sequence_length = 10
features_per_timestep = 5  # hour, location_encoded, direction, time_since_last, zone_risk

# Build LSTM Autoencoder
encoder_input = tf.keras.Input(shape=(sequence_length, features_per_timestep))

# Encoder
encoded = LSTM(64, activation='relu', return_sequences=True)(encoder_input)
encoded = LSTM(32, activation='relu', return_sequences=False)(encoded)

# Decoder
decoded = RepeatVector(sequence_length)(encoded)
decoded = LSTM(32, activation='relu', return_sequences=True)(decoded)
decoded = LSTM(64, activation='relu', return_sequences=True)(decoded)
decoded = TimeDistributed(Dense(features_per_timestep))(decoded)

# Autoencoder model
autoencoder = Model(encoder_input, decoded)
autoencoder.compile(optimizer='adam', loss='mse')

# Train on normal sequences only
X_train_sequences = create_sequences(normal_data, sequence_length)
autoencoder.fit(
    X_train_sequences, X_train_sequences,
    epochs=50,
    batch_size=32,
    validation_split=0.2
)

# Detect anomalies (high reconstruction error = anomaly)
X_test_sequences = create_sequences(test_data, sequence_length)
reconstructed = autoencoder.predict(X_test_sequences)
reconstruction_errors = np.mean(np.abs(X_test_sequences - reconstructed), axis=(1, 2))

# Threshold: 95th percentile of training reconstruction errors
threshold = np.percentile(reconstruction_errors_train, 95)
anomalies = reconstruction_errors > threshold
```

**Expected Performance:**
- **Precision:** 30-50% (better than Isolation Forest for temporal patterns)
- **Recall:** 70-85%
- **Training Time:** 10-30 minutes (GPU recommended)
- **Inference Latency:** 20-50ms per sequence

**Pros:**
- Detects **sequence anomalies** rules cannot catch
- Learns entity-specific normal behavior patterns
- Can adapt to slowly changing patterns (retrain weekly)
- Captures temporal dependencies

**Cons:**
- Requires more data (1000+ sequences per entity ideal)
- Harder to interpret than Isolation Forest
- Needs GPU for efficient training
- Hyperparameter tuning required (sequence length, LSTM units, threshold)

**Verdict:** ✅ **RECOMMENDED for Phase 2** (after Isolation Forest validated)

---

#### Option B: Prophet (Facebook Time-Series)

**Algorithm:** Facebook Prophet

**Why It Might Fit:**
- ✅ Detects anomalies in time-series occupancy data
- ✅ Handles seasonality (daily/weekly patterns)
- ✅ Easy to interpret (forecasts vs actuals)

**Use Case:**
- Detect unusual occupancy spikes in zones (e.g., library crowded at 3am)

**Implementation:**
```python
from prophet import Prophet
import pandas as pd

# Prepare time-series data (zone occupancy over time)
df = pd.DataFrame({
    'ds': timestamps,  # Datetime column
    'y': occupancy     # Metric to forecast
})

# Train Prophet
model = Prophet(
    interval_width=0.95,    # 95% confidence interval
    changepoint_prior_scale=0.05  # Detect trend changes
)
model.fit(df)

# Forecast
future = model.make_future_dataframe(periods=24, freq='H')
forecast = model.predict(future)

# Detect anomalies (actual outside confidence interval)
df_merged = df.merge(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds')
anomalies = df_merged[
    (df_merged['y'] < df_merged['yhat_lower']) |
    (df_merged['y'] > df_merged['yhat_upper'])
]
```

**Pros:**
- Simple to implement and interpret
- Handles seasonality automatically
- No deep learning required

**Cons:**
- ❌ **Only works for single time-series** (zone occupancy, not entity behavior)
- ❌ Cannot detect entity-level anomalies (card sharing, impossible travel)
- ❌ Not suitable for multi-variate data

**Expected Performance:**
- **Precision:** 40-60% (for occupancy anomalies only)
- **Recall:** 70-80%

**Verdict:** ⚠️ **LIMITED USE CASE** (only for zone-level occupancy anomalies, not entity behavior)

---

#### Option C: ARIMA

**Algorithm:** AutoRegressive Integrated Moving Average

**Why It Might Fit:**
- ✅ Classic statistical method for time-series anomaly detection
- ✅ Works well for stationary time-series

**Cons:**
- ❌ Assumes stationarity (campus access patterns are non-stationary)
- ❌ Requires manual parameter tuning (p, d, q)
- ❌ Less effective than Prophet or LSTM for complex patterns

**Verdict:** ❌ **NOT RECOMMENDED** (Prophet or LSTM are better choices)

---

### 3.4 Statistical Methods ⚠️ PARTIALLY ALREADY IMPLEMENTED

#### Current Implementation (Already in Use)

The current rule-based system **already uses statistical thresholds**:
- Overcrowding: `occupancy > capacity` (fixed threshold)
- Underutilization: `occupancy < 0.2 * capacity` (20th percentile)
- Excessive access: `>10 swipes/hour` (fixed threshold)

**These are simple statistical methods**, not ML.

#### Advanced Statistical Methods (Not Currently Used)

**Z-Score Anomaly Detection:**
```python
from scipy import stats
import numpy as np

# Calculate z-scores for access frequency
access_counts = entity_access_data.groupby('entity_id').size()
z_scores = np.abs(stats.zscore(access_counts))

# Flag anomalies (z-score > 3 = 99.7% confidence)
anomalies = access_counts[z_scores > 3]
```

**IQR (Interquartile Range) Method:**
```python
# Calculate IQR for dwell time
Q1 = dwell_times.quantile(0.25)
Q3 = dwell_times.quantile(0.75)
IQR = Q3 - Q1

# Outliers: values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
anomalies = dwell_times[(dwell_times < lower_bound) | (dwell_times > upper_bound)]
```

**Pros:**
- ✅ Fast, interpretable, no training required
- ✅ Works well for univariate data (single metric)
- ✅ Statistically grounded (confidence intervals)

**Cons:**
- ❌ Assumes normal distribution (access patterns may not be normal)
- ❌ Cannot handle multi-variate anomalies
- ❌ Fixed thresholds do not adapt

**Verdict:** ⚠️ **ALREADY PARTIALLY IN USE** (rules are statistical thresholds)

---

### 3.5 Deep Learning (Advanced) ⚠️ OVERKILL FOR CURRENT SCALE

#### Variational Autoencoder (VAE)

**Algorithm:** VAE for anomaly detection

**Why It Might Fit:**
- ✅ Learns complex latent representations
- ✅ Probabilistic framework (uncertainty quantification)

**Cons:**
- ❌ **Requires large datasets** (100K+ records for effective training)
- ❌ Computationally expensive (GPU required)
- ❌ Hard to interpret
- ❌ Overkill for 32K records

**Verdict:** ❌ **NOT RECOMMENDED** (dataset too small, complexity not justified)

---

#### Generative Adversarial Network (GAN)

**Algorithm:** GAN-based anomaly detection

**Cons:**
- ❌ **Training instability** (GANs are hard to train)
- ❌ Requires 100K+ records
- ❌ Not interpretable
- ❌ No clear advantage over simpler methods

**Verdict:** ❌ **NOT RECOMMENDED**

---

## 4. Critical Decision Factors

### 4.1 Do We Have Labeled Anomaly Data?

**Answer:** ❌ **NO**

**Evidence:**
- No `anomaly_label` field in card swipe data
- `cache_anomalies.py` stores detected anomalies but no validation labels
- No "true positive" / "false positive" annotations from security team

**Implication:**
- ❌ Cannot use supervised methods (XGBoost, Random Forest)
- ✅ Must use unsupervised methods (Isolation Forest, LSTM Autoencoder)

**Action Required:**
If supervised learning desired in future:
1. Security team reviews cached anomalies in PostgreSQL
2. Labels each anomaly as: `true_positive`, `false_positive`, `uncertain`
3. Collect 500-1000 labeled examples
4. Then train XGBoost classifier

---

### 4.2 Are Current Rules Missing Anomalies?

**Answer:** ⚠️ **UNKNOWN (No Validation Metrics)**

**Evidence:**
- No precision/recall metrics tracked
- No false positive rate monitoring
- No comparison to ground truth (no security incident log)

**Likely Missed Anomaly Types:**
1. **Slow-evolving patterns** - Gradually shifting access times (rules use fixed thresholds)
2. **Multi-entity collusion** - Coordinated card sharing across multiple people
3. **Legitimate edge cases flagged as anomalies** - Emergency access, maintenance workers
4. **Novel attack patterns** - New security threats not anticipated by rule designers
5. **Context-dependent anomalies** - Same behavior normal in one context, anomalous in another

**Example ML Could Catch (Rules Cannot):**
- Entity normally accesses lab at 9am-5pm. Over 3 months, gradually shifts to 11pm-3am access.
- Rules: No violation (still within operating hours)
- LSTM Autoencoder: Flags as anomaly (temporal pattern shift)

**Verdict:** ✅ **ML CAN ADD VALUE** by discovering unknown patterns

---

### 4.3 Are There Too Many False Positives?

**Answer:** ⚠️ **UNKNOWN (No Monitoring)**

**Evidence:**
- No false positive rate tracked in code
- No alert fatigue metrics
- No security team feedback on anomaly quality

**Hypothetical Scenarios Where Rules May Over-Alert:**
1. **Maintenance workers** - Legitimate off-hours access flagged
2. **Faculty with flexible schedules** - Late-night lab access flagged as off-hours violation
3. **Students with special permissions** - Cross-department access flagged
4. **Broken card readers** - Duplicate swipes flagged as consecutive same-direction

**How ML Could Help:**
- Supervised ML (if labels available): Learn patterns of false positives, suppress them
- Anomaly scoring: Rank alerts by severity (focus on high-confidence anomalies first)

**Verdict:** ⚠️ **NEED MONITORING** before determining if ML reduces false positives

---

### 4.4 Is Interpretability Critical?

**Answer:** ✅ **YES (Campus Security Context)**

**Requirements:**
- Security personnel must explain why an alert was triggered
- Disciplinary actions require justifiable evidence
- Student appeals need clear rule violations documented

**Interpretability by Method:**

| Method | Interpretability | Explanation Capability |
|--------|-----------------|------------------------|
| Rule-based | ✅✅✅ Excellent | "Student accessed faculty room (policy violation)" |
| Isolation Forest | ⚠️ Moderate | "Anomaly score: 0.85 (unusual pattern)" |
| LSTM Autoencoder | ❌ Poor | "High reconstruction error (abnormal sequence)" |
| XGBoost (supervised) | ⚠️ Moderate | "Top factors: late hour (0.4), role mismatch (0.3)" |

**Mitigation Strategies for ML:**
1. **Hybrid approach:** ML flags anomaly → trigger relevant rule check → explain via rule
2. **SHAP values:** Explain XGBoost predictions with feature contributions
3. **Anomaly scoring:** Rank alerts, security team investigates top 10 daily
4. **Clustering:** Group similar anomalies, define new rules based on clusters

**Example Hybrid Explanation:**
```
Anomaly Detected (Isolation Forest Score: 0.92)
Triggering Rule: Impossible Travel Detection
Details: Entity E12345 exited LAB_101 at 14:03 and entered HOSTEL_GATE at 14:04 (1 minute apart, 2km distance)
Recommended Action: Investigate card sharing
```

**Verdict:** ✅ **HYBRID APPROACH REQUIRED** (ML discovers, rules explain)

---

## 5. Recommended Implementation Plan

### Phase 1: Hybrid Foundation (Months 1-3)

**Objective:** Keep all rules, add Isolation Forest to discover unknown anomalies

**Steps:**
1. **Feature Engineering** (Week 1-2)
   ```python
   # Extract features for Isolation Forest
   features = pd.DataFrame({
       'hour': df['timestamp'].dt.hour,
       'day_of_week': df['timestamp'].dt.dayofweek,
       'is_weekend': df['timestamp'].dt.dayofweek >= 5,
       'is_peak_hour': df['timestamp'].dt.hour.isin([9,10,11,14,15,16,17]),
       'time_since_last_access_hours': time_diffs,
       'access_frequency_1h': rolling_1h_counts,
       'access_frequency_24h': rolling_24h_counts,
       'zone_encoded': label_encode(df['location']),
       'direction_encoded': (df['IN_OUT'] == 'IN').astype(int),
       'hour_sin': np.sin(2 * np.pi * df['timestamp'].dt.hour / 24),
       'hour_cos': np.cos(2 * np.pi * df['timestamp'].dt.hour / 24),
       'day_sin': np.sin(2 * np.pi * df['timestamp'].dt.dayofweek / 7),
       'day_cos': np.cos(2 * np.pi * df['timestamp'].dt.dayofweek / 7),
   })
   ```

2. **Train Isolation Forest** (Week 2)
   ```python
   from sklearn.ensemble import IsolationForest

   iso_forest = IsolationForest(
       n_estimators=200,
       contamination=0.05,  # Start conservatively (5% anomaly rate)
       max_samples=256,
       random_state=42,
       n_jobs=-1
   )

   iso_forest.fit(features)
   joblib.dump(iso_forest, 'models/isolation_forest_v1.joblib')
   ```

3. **Create ML Anomaly Detection Service** (Week 3)
   ```python
   # File: backend/services/ml_anomaly_detection.py

   class MLAnomalyDetectionService:
       def __init__(self):
           self.model = joblib.load('models/isolation_forest_v1.joblib')
           self.feature_engineer = FeatureEngineer()

       def detect_anomalies(self, events: List[Dict]) -> List[Dict]:
           """Detect anomalies using Isolation Forest"""
           features = self.feature_engineer.extract_features(events)
           predictions = self.model.predict(features)
           scores = self.model.score_samples(features)

           anomalies = []
           for i, (pred, score) in enumerate(zip(predictions, scores)):
               if pred == -1:  # Anomaly
                   anomalies.append({
                       'id': f"ml_anomaly_{events[i]['timestamp']}",
                       'type': 'ml_detected_anomaly',
                       'severity': self._score_to_severity(score),
                       'timestamp': events[i]['timestamp'],
                       'entity_id': events[i]['entity_id'],
                       'location': events[i]['location'],
                       'anomaly_score': float(score),
                       'description': f"ML-detected anomaly (score: {score:.3f})",
                       'details': {
                           'model_version': 'isolation_forest_v1',
                           'anomaly_score': float(score),
                           'features': features.iloc[i].to_dict()
                       },
                       'recommended_actions': [
                           "Review access pattern manually",
                           "Check if matches known rule violations",
                           "Investigate for novel security threat"
                       ]
                   })

           return anomalies

       def _score_to_severity(self, score: float) -> str:
           """Map anomaly score to severity level"""
           if score < -0.5:
               return 'critical'
           elif score < -0.3:
               return 'high'
           elif score < -0.1:
               return 'medium'
           else:
               return 'low'
   ```

4. **Integrate with Existing Anomaly Detection** (Week 4)
   ```python
   # Update backend/services/anomaly_detection.py

   def detect_all_anomalies(self, ...):
       anomalies = []

       # Existing rule-based detections
       anomalies.extend(self._detect_overcrowding_simplified(...))
       anomalies.extend(self._detect_underutilization_simplified(...))
       # ... all existing rules

       # NEW: Add ML-detected anomalies
       if include_ml_anomalies:
           try:
               ml_service = MLAnomalyDetectionService()
               ml_anomalies = ml_service.detect_anomalies(card_swipes)
               anomalies.extend(ml_anomalies)
               logger.info(f"ML detected {len(ml_anomalies)} additional anomalies")
           except Exception as e:
               logger.warning(f"ML anomaly detection failed: {e}")

       return anomalies
   ```

5. **Monitoring & Tuning** (Weeks 5-12)
   - Security team reviews ML-flagged anomalies daily
   - Track metrics:
     - ML anomalies per day
     - Overlap with rule-based anomalies
     - False positive rate (security team feedback)
   - Tune `contamination` parameter based on feedback
   - Add/remove features based on importance

**Expected Outcomes:**
- ✅ Discover 5-15 new anomaly patterns not covered by rules
- ✅ Baseline false positive rate established
- ✅ Security team comfortable with ML-assisted detection

**Success Metrics:**
- ML discovers ≥3 novel anomaly types in first month
- False positive rate <20% (lower than rule-based if possible)
- Security team reviews 100% of ML anomalies for validation

---

### Phase 2: Time-Series Anomaly Detection (Months 4-6)

**Objective:** Add LSTM Autoencoder for temporal pattern anomalies

**Steps:**
1. **Prepare Sequential Data** (Week 1)
   ```python
   def create_entity_sequences(entity_id: str, sequence_length: int = 10):
       """Create sequences of last N access events per entity"""
       events = get_entity_timeline(entity_id)
       events = events.sort_values('timestamp')

       sequences = []
       for i in range(len(events) - sequence_length):
           seq = events.iloc[i:i+sequence_length]
           sequences.append({
               'entity_id': entity_id,
               'sequence': extract_features(seq),
               'target': events.iloc[i+sequence_length]  # Next event
           })

       return sequences
   ```

2. **Train LSTM Autoencoder** (Weeks 2-3)
   - Train per entity (personalized models) or global model
   - Use only "normal" sequences (filter out known rule violations)
   - GPU recommended (can use Colab if no local GPU)

3. **Real-Time Anomaly Detection** (Week 4)
   ```python
   class TemporalAnomalyDetector:
       def __init__(self):
           self.autoencoder = tf.keras.models.load_model('models/lstm_autoencoder.h5')
           self.threshold = 0.05  # Reconstruction error threshold

       def detect_sequence_anomaly(self, entity_id: str) -> Optional[Dict]:
           """Detect anomaly in entity's recent access sequence"""
           recent_events = get_last_n_events(entity_id, n=10)
           sequence = extract_features(recent_events)

           # Reconstruct sequence
           reconstructed = self.autoencoder.predict(sequence.reshape(1, 10, 5))
           reconstruction_error = np.mean(np.abs(sequence - reconstructed))

           if reconstruction_error > self.threshold:
               return {
                   'type': 'temporal_anomaly',
                   'entity_id': entity_id,
                   'reconstruction_error': float(reconstruction_error),
                   'severity': 'high' if reconstruction_error > 0.1 else 'medium',
                   'description': f"Unusual access sequence pattern detected (error: {reconstruction_error:.3f})"
               }

           return None
   ```

4. **Validation & Tuning** (Weeks 5-8)
   - Compare with Isolation Forest results
   - Identify patterns LSTM catches that Isolation Forest misses
   - Tune sequence length (try 5, 10, 20)
   - Adjust reconstruction error threshold

**Expected Outcomes:**
- ✅ Detect 3-5 new temporal anomaly types (e.g., gradually shifting access times)
- ✅ Reduce false positives by 10-20% vs Isolation Forest alone

---

### Phase 3: Supervised Learning (Months 7+, CONDITIONAL)

**Pre-Requisite:** ✅ Security team has labeled 500-1000 anomalies

**Objective:** Train XGBoost classifier to reduce false positives and prioritize alerts

**Steps:**
1. **Data Labeling Campaign** (Months 4-6, parallel to Phase 2)
   - Security team reviews all ML + rule-based anomalies
   - Labels each as: `true_positive`, `false_positive`, `uncertain`
   - Store in PostgreSQL:
   ```sql
   ALTER TABLE anomalies ADD COLUMN label VARCHAR(20);
   ALTER TABLE anomalies ADD COLUMN labeled_by VARCHAR(50);
   ALTER TABLE anomalies ADD COLUMN labeled_at TIMESTAMP;
   ```

2. **Train XGBoost Classifier** (Week 1-2)
   ```python
   from xgboost import XGBClassifier
   from sklearn.model_selection import train_test_split
   from sklearn.metrics import classification_report, confusion_matrix

   # Load labeled anomalies
   labeled_data = pd.read_sql(
       "SELECT * FROM anomalies WHERE label IN ('true_positive', 'false_positive')",
       db_connection
   )

   # Feature engineering
   features = extract_features(labeled_data)
   labels = (labeled_data['label'] == 'true_positive').astype(int)

   # Train/test split
   X_train, X_test, y_train, y_test = train_test_split(
       features, labels, test_size=0.2, stratify=labels, random_state=42
   )

   # Train XGBoost
   xgb_model = XGBClassifier(
       n_estimators=100,
       max_depth=6,
       learning_rate=0.1,
       scale_pos_weight=10,  # Handle class imbalance
       eval_metric='logloss',
       random_state=42
   )

   xgb_model.fit(
       X_train, y_train,
       eval_set=[(X_test, y_test)],
       early_stopping_rounds=10,
       verbose=True
   )

   # Evaluate
   y_pred = xgb_model.predict(X_test)
   print(classification_report(y_test, y_pred))
   print(confusion_matrix(y_test, y_pred))
   ```

3. **Deploy as Anomaly Prioritization Layer** (Week 3)
   ```python
   class AnomalyPrioritizationService:
       def __init__(self):
           self.xgb_model = joblib.load('models/xgb_prioritizer_v1.joblib')

       def prioritize_anomalies(self, anomalies: List[Dict]) -> List[Dict]:
           """Add ML-based priority scores to anomalies"""
           features = extract_features_from_anomalies(anomalies)
           true_positive_probs = self.xgb_model.predict_proba(features)[:, 1]

           for anomaly, prob in zip(anomalies, true_positive_probs):
               anomaly['ml_priority_score'] = float(prob)
               anomaly['ml_confidence'] = 'high' if prob > 0.8 else 'medium' if prob > 0.5 else 'low'

           # Sort by priority score
           return sorted(anomalies, key=lambda x: x['ml_priority_score'], reverse=True)
   ```

4. **A/B Testing** (Weeks 4-8)
   - 50% of security team sees ML-prioritized alerts
   - 50% sees traditional severity-based alerts
   - Measure: Time to triage, false positive reduction

**Expected Outcomes:**
- ✅ Reduce false positive rate by 30-50%
- ✅ Security team focuses on high-priority alerts first
- ✅ 20-30% time savings in anomaly triage

---

## 6. Production Integration Strategy

### 6.1 API Design

**Add ML Anomaly Detection Endpoint:**
```python
# File: backend/anomaly_routes.py

@router.get("/api/v1/anomalies/ml")
async def get_ml_anomalies(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_score: float = -0.3,  # Only return high-confidence anomalies
    limit: int = 100
):
    """Get ML-detected anomalies"""
    ml_service = MLAnomalyDetectionService()
    anomalies = ml_service.detect_anomalies(
        start_date=start_date,
        end_date=end_date,
        min_score=min_score
    )

    return {
        'total': len(anomalies),
        'anomalies': anomalies[:limit],
        'model_version': 'isolation_forest_v1'
    }

@router.get("/api/v1/anomalies/combined")
async def get_combined_anomalies(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_ml: bool = True,
    include_rules: bool = True
):
    """Get combined rule + ML anomalies"""
    anomalies = []

    if include_rules:
        rule_service = AnomalyDetectionService(...)
        rule_anomalies = rule_service.detect_all_anomalies(start_date, end_date)
        anomalies.extend(rule_anomalies)

    if include_ml:
        ml_service = MLAnomalyDetectionService()
        ml_anomalies = ml_service.detect_anomalies(start_date, end_date)
        anomalies.extend(ml_anomalies)

    # Deduplicate and merge overlapping anomalies
    deduplicated = deduplicate_anomalies(anomalies)

    return {
        'total': len(deduplicated),
        'rule_based': len([a for a in deduplicated if a['type'] != 'ml_detected_anomaly']),
        'ml_detected': len([a for a in deduplicated if a['type'] == 'ml_detected_anomaly']),
        'anomalies': deduplicated
    }
```

### 6.2 Deduplication Strategy

**Problem:** ML may flag same anomaly as rules (overlap)

**Solution:**
```python
def deduplicate_anomalies(anomalies: List[Dict]) -> List[Dict]:
    """Merge overlapping anomalies from rules and ML"""
    merged = {}

    for anomaly in anomalies:
        key = (anomaly['entity_id'], anomaly['location'], anomaly['timestamp'])

        if key in merged:
            # Merge: keep rule-based explanation, add ML score
            existing = merged[key]
            if anomaly['type'] == 'ml_detected_anomaly':
                existing['ml_score'] = anomaly.get('anomaly_score', 0)
                existing['ml_confirmed'] = True
            else:
                merged[key] = anomaly
        else:
            merged[key] = anomaly

    return list(merged.values())
```

### 6.3 Monitoring & Alerting

**Add ML Model Performance Monitoring:**
```python
from prometheus_client import Counter, Histogram

ml_anomaly_counter = Counter(
    'ml_anomalies_detected_total',
    'Total ML anomalies detected',
    ['model_version', 'severity']
)

ml_inference_latency = Histogram(
    'ml_anomaly_detection_latency_seconds',
    'ML anomaly detection latency',
    ['model_version']
)

def detect_anomalies_with_monitoring(events):
    import time
    start = time.time()

    anomalies = ml_service.detect_anomalies(events)

    latency = time.time() - start
    ml_inference_latency.labels(model_version='v1').observe(latency)

    for anomaly in anomalies:
        ml_anomaly_counter.labels(
            model_version='v1',
            severity=anomaly['severity']
        ).inc()

    return anomalies
```

---

## 7. Cost-Benefit Analysis

### 7.1 Implementation Costs

| Phase | Effort | Timeline | Cost (Person-Hours) |
|-------|--------|----------|---------------------|
| Phase 1: Isolation Forest | Data engineer | 4 weeks | 120 hours |
| Phase 2: LSTM Autoencoder | ML engineer | 8 weeks | 200 hours |
| Phase 3: Supervised XGBoost | ML engineer + security team | 12 weeks | 150 hours + labeling |
| **Total** | | **6 months** | **470 hours** |

**Estimated Cost:** $50-80K (fully-loaded cost for ML engineer)

### 7.2 Operational Costs

| Component | Cost | Frequency |
|-----------|------|-----------|
| Model retraining | 2 hours/week | Weekly |
| False positive review | 1 hour/day | Daily |
| Model monitoring | 0.5 hours/day | Daily |
| GPU instance (optional) | $100/month | Monthly |

**Annual Operational Cost:** $15-20K

### 7.3 Expected Benefits

| Benefit | Estimated Value | Confidence |
|---------|----------------|------------|
| Discover 10-20 new anomaly types | High impact | High |
| Reduce false positives by 30% | 5 hours/week saved | Medium |
| Early detection of novel threats | Risk mitigation | Medium |
| Automated anomaly discovery | $20K/year saved | Low |

**ROI:** Positive if ML discovers ≥5 high-value anomalies in first year

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| High false positive rate | High | Medium | Start with low contamination (0.05), tune based on feedback |
| Model drift over time | Medium | High | Weekly retraining, drift monitoring |
| ML misses critical anomalies | Low | Critical | **Hybrid approach** - rules always run |
| Interpretability issues | High | Medium | Use SHAP, hybrid explanations |
| Insufficient training data | Low | Medium | 32K records sufficient for unsupervised |

### 8.2 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Security team overwhelmed by alerts | Medium | High | Anomaly prioritization with XGBoost (Phase 3) |
| Lack of labeled data for supervised | High | Medium | Labeling campaign in parallel to Phase 2 |
| Model maintenance burden | Medium | Medium | Automated retraining pipeline |
| GPU dependency (LSTM) | Low | Low | Use CPU for inference, GPU only for training |

### 8.3 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| No measurable improvement | Medium | High | A/B testing, clear success metrics |
| Budget overruns | Low | Medium | Phased approach, validate ROI after Phase 1 |
| Resistance to ML adoption | Medium | Medium | Security team training, clear explanations |

---

## 9. Success Metrics & KPIs

### Phase 1 Success Criteria (Months 1-3)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Novel anomalies discovered | ≥3 types | Manual review by security team |
| False positive rate | <20% | Security team labeling |
| Inference latency | <50ms per event | Prometheus monitoring |
| Model training time | <5 minutes | MLflow tracking |
| Overlap with rule-based | 30-50% | Automated comparison |

### Phase 2 Success Criteria (Months 4-6)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Temporal anomalies detected | ≥5 new patterns | Security team validation |
| LSTM reconstruction error distribution | Clear separation | Histogram analysis |
| Inference latency (LSTM) | <100ms per sequence | Monitoring |
| False positive reduction | 10-20% vs Phase 1 | A/B testing |

### Phase 3 Success Criteria (Months 7+)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Labeled anomalies collected | 500-1000 | PostgreSQL count |
| XGBoost accuracy | >85% | Test set evaluation |
| False positive reduction | 30-50% | Security team feedback |
| Time to triage anomalies | -20% reduction | Security team survey |

---

## 10. Comparison Summary

### When to Keep Rules (✅ ALWAYS)

**Strengths:**
- 100% interpretable
- No training data required
- Deterministic, predictable
- Legally defensible (clear policy violations)
- Fast execution (<1ms per check)

**Use Cases:**
- Policy violations (off-hours, role mismatches)
- Safety-critical alerts (curfew violations, impossible travel)
- Real-time alerts (overcrowding)

**Verdict:** ✅ **KEEP ALL RULES** - They provide essential baseline security

---

### When to Add ML (✅ RECOMMENDED)

**Strengths:**
- Discovers unknown patterns
- Adapts to changing behavior
- Learns from data
- Can reduce false positives (supervised)

**Use Cases:**
- Novel attack detection
- Behavioral drift detection
- Complex multi-variate anomalies
- Alert prioritization

**Verdict:** ✅ **ADD ML IN HYBRID APPROACH**

---

### Recommended Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   ANOMALY DETECTION SYSTEM                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────┐      ┌─────────────────────────┐  │
│  │   RULE-BASED (19)   │      │   ML-BASED (3 MODELS)   │  │
│  ├─────────────────────┤      ├─────────────────────────┤  │
│  │ • Off-hours access  │      │ • Isolation Forest      │  │
│  │ • Role violations   │      │   (unknown anomalies)   │  │
│  │ • Impossible travel │      │                         │  │
│  │ • Curfew violations │      │ • LSTM Autoencoder      │  │
│  │ • Tailgating        │      │   (temporal patterns)   │  │
│  │ • ... (14 more)     │      │                         │  │
│  │                     │      │ • XGBoost (supervised)  │  │
│  │ Always Runs         │      │   (prioritization)      │  │
│  └──────────┬──────────┘      └──────────┬──────────────┘  │
│             │                             │                  │
│             └──────────┬──────────────────┘                  │
│                        │                                     │
│              ┌─────────▼──────────┐                          │
│              │  DEDUPLICATION &   │                          │
│              │  MERGE LOGIC       │                          │
│              └─────────┬──────────┘                          │
│                        │                                     │
│              ┌─────────▼──────────┐                          │
│              │  PRIORITIZATION    │                          │
│              │  (ML Priority      │                          │
│              │   Score + Rules)   │                          │
│              └─────────┬──────────┘                          │
│                        │                                     │
│              ┌─────────▼──────────┐                          │
│              │  ALERT DASHBOARD   │                          │
│              │  (Security Team)   │                          │
│              └────────────────────┘                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Final Recommendation

### HYBRID APPROACH: Rules + Unsupervised ML

**Phase 1 (Immediate):** ✅ **IMPLEMENT NOW**
- Keep all 19 rule-based anomaly detectors (no changes)
- Add Isolation Forest for unknown anomaly discovery
- Run both in parallel, deduplicate results
- Security team validates ML anomalies for 3 months

**Phase 2 (4-6 months):** ✅ **IMPLEMENT IF PHASE 1 SUCCESSFUL**
- Add LSTM Autoencoder for temporal anomalies
- Focus on entity behavioral drift detection
- Validate reduces false positives vs Isolation Forest

**Phase 3 (7+ months):** ⚠️ **CONDITIONAL ON LABELING**
- Train XGBoost classifier for alert prioritization
- Requires 500-1000 labeled anomalies from security team
- Expected 30-50% false positive reduction

### Why This Approach?

1. **No Labeled Data** → Unsupervised methods only viable option
2. **Interpretability Critical** → Rules provide explanations, ML discovers patterns
3. **Low Risk** → Hybrid approach ensures no regressions (rules always run)
4. **Incremental Value** → Each phase adds new capability without disrupting existing
5. **Cost-Effective** → Start with low-cost Isolation Forest, validate before LSTM investment

### Decision Criteria

**Proceed with Phase 1 if:**
- ✅ Security team willing to review ML anomalies for 3 months
- ✅ Data engineering capacity available (120 hours over 4 weeks)
- ✅ Budget approved for $15-20K annual operational cost

**Abort if:**
- ❌ False positive rate >50% after tuning
- ❌ No novel anomalies discovered in first 2 months
- ❌ Security team overwhelmed by alert volume

### Next Steps

1. **Week 1:** Present this analysis to security team + engineering leadership
2. **Week 2:** Get approval + budget allocation for Phase 1
3. **Week 3-4:** Feature engineering + Isolation Forest training
4. **Week 5-12:** Validation, tuning, monitoring
5. **Month 4:** Phase 1 retrospective → decide on Phase 2

---

## 12. Appendix: Code Examples

### A. Feature Engineering Pipeline

```python
# File: backend/services/ml/feature_engineering.py

import pandas as pd
import numpy as np
from typing import List, Dict
from sklearn.preprocessing import LabelEncoder

class AnomalyFeatureEngineer:
    def __init__(self):
        self.location_encoder = LabelEncoder()
        self.role_encoder = LabelEncoder()

    def extract_features(self, card_swipes: pd.DataFrame) -> pd.DataFrame:
        """Extract features for anomaly detection"""

        # Temporal features
        df = card_swipes.copy()
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'] >= 5
        df['is_peak_hour'] = df['hour'].isin([9,10,11,14,15,16,17])
        df['is_night'] = df['hour'].isin([0,1,2,3,4,5,23])

        # Cyclic encoding
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        # Frequency features
        df = df.sort_values(['card_id', 'timestamp'])
        df['time_since_last_access'] = df.groupby('card_id')['timestamp'].diff().dt.total_seconds() / 3600
        df['access_count_1h'] = df.groupby('card_id').rolling(window='1H', on='timestamp').size()
        df['access_count_24h'] = df.groupby('card_id').rolling(window='24H', on='timestamp').size()

        # Categorical encoding
        df['location_encoded'] = self.location_encoder.fit_transform(df['location_id'])
        df['direction_encoded'] = (df['IN_OUT'] == 'IN').astype(int)

        # Zone-specific features
        zone_risk_scores = {
            'LAB_305': 0.9,  # High security
            'ROOM_A1': 0.8,
            'ROOM_A2': 0.8,
            'HOSTEL_GATE': 0.6,
            'LIB_ENT': 0.3,
            'CAF_01': 0.2
        }
        df['zone_risk_score'] = df['location_id'].map(zone_risk_scores).fillna(0.5)

        # Select final features
        feature_columns = [
            'hour', 'day_of_week', 'is_weekend', 'is_peak_hour', 'is_night',
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
            'time_since_last_access', 'access_count_1h', 'access_count_24h',
            'location_encoded', 'direction_encoded', 'zone_risk_score'
        ]

        return df[feature_columns].fillna(0)
```

### B. Isolation Forest Training Script

```python
# File: backend/scripts/train_isolation_forest.py

import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from backend.services.ml.feature_engineering import AnomalyFeatureEngineer

def train_isolation_forest():
    # Load data
    print("Loading card swipe data...")
    df = pd.read_csv('backend/augmented/campus_card_swipes_augmented.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Feature engineering
    print("Extracting features...")
    feature_engineer = AnomalyFeatureEngineer()
    features = feature_engineer.extract_features(df)

    print(f"Training on {len(features)} records with {features.shape[1]} features")

    # Train Isolation Forest
    print("Training Isolation Forest...")
    iso_forest = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        max_samples=256,
        random_state=42,
        n_jobs=-1,
        verbose=1
    )

    iso_forest.fit(features)

    # Evaluate on training data (just to see distribution)
    predictions = iso_forest.predict(features)
    scores = iso_forest.score_samples(features)

    anomaly_count = (predictions == -1).sum()
    anomaly_rate = anomaly_count / len(predictions)

    print(f"\nTraining Results:")
    print(f"Total samples: {len(features)}")
    print(f"Anomalies detected: {anomaly_count}")
    print(f"Anomaly rate: {anomaly_rate:.2%}")
    print(f"Score range: [{scores.min():.3f}, {scores.max():.3f}]")

    # Save model
    print("\nSaving model...")
    joblib.dump(iso_forest, 'backend/models/isolation_forest_v1.joblib')
    joblib.dump(feature_engineer, 'backend/models/feature_engineer_v1.joblib')

    print("Model saved successfully!")

    # Show example anomalies
    print("\nExample anomalies (top 10 by score):")
    df_with_scores = df.copy()
    df_with_scores['anomaly_score'] = scores
    df_with_scores['is_anomaly'] = predictions == -1

    top_anomalies = df_with_scores[df_with_scores['is_anomaly']].sort_values('anomaly_score').head(10)
    print(top_anomalies[['card_id', 'location_id', 'timestamp', 'IN_OUT', 'anomaly_score']])

if __name__ == "__main__":
    train_isolation_forest()
```

### C. Real-Time Anomaly Detection API

```python
# File: backend/services/ml_anomaly_detection.py

import joblib
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

class MLAnomalyDetectionService:
    def __init__(self):
        self.model = joblib.load('backend/models/isolation_forest_v1.joblib')
        self.feature_engineer = joblib.load('backend/models/feature_engineer_v1.joblib')

    def detect_anomalies(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_score: float = -0.3
    ) -> List[Dict]:
        """Detect anomalies in card swipe data"""

        # Load data
        df = pd.read_csv('backend/augmented/campus_card_swipes_augmented.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Filter by date range
        if start_date:
            df = df[df['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['timestamp'] <= pd.to_datetime(end_date)]

        # Extract features
        features = self.feature_engineer.extract_features(df)

        # Predict
        predictions = self.model.predict(features)
        scores = self.model.score_samples(features)

        # Filter anomalies
        anomaly_mask = (predictions == -1) & (scores <= min_score)
        anomaly_df = df[anomaly_mask].copy()
        anomaly_df['anomaly_score'] = scores[anomaly_mask]

        # Convert to anomaly dicts
        anomalies = []
        for _, row in anomaly_df.iterrows():
            anomalies.append({
                'id': f"ml_anomaly_{row['timestamp'].isoformat()}_{row['card_id']}",
                'type': 'ml_detected_anomaly',
                'severity': self._score_to_severity(row['anomaly_score']),
                'timestamp': row['timestamp'].isoformat(),
                'entity_id': row.get('entity_id', row['card_id']),
                'location': row['location_id'],
                'anomaly_score': float(row['anomaly_score']),
                'description': f"ML-detected anomaly (score: {row['anomaly_score']:.3f})",
                'details': {
                    'model_version': 'isolation_forest_v1',
                    'anomaly_score': float(row['anomaly_score']),
                    'direction': row['IN_OUT'],
                    'hour': row['timestamp'].hour
                },
                'recommended_actions': [
                    "Review access pattern for unusual behavior",
                    "Check if matches known rule violations",
                    "Investigate for novel security threat",
                    "Validate with CCTV footage if available"
                ]
            })

        return sorted(anomalies, key=lambda x: x['anomaly_score'])

    def _score_to_severity(self, score: float) -> str:
        """Map anomaly score to severity level"""
        if score < -0.5:
            return 'critical'
        elif score < -0.3:
            return 'high'
        elif score < -0.1:
            return 'medium'
        else:
            return 'low'
```

---

**End of Report**

**Next Action:** Present to stakeholders for approval to proceed with Phase 1.
