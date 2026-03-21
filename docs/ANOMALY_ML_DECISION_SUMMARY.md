# Anomaly Detection ML Decision - Executive Summary

**Date:** 2026-03-15
**Recommendation:** HYBRID APPROACH - Keep Rules + Add Unsupervised ML
**Confidence:** High (based on data analysis and production requirements)

---

## TL;DR

**DON'T REPLACE - AUGMENT**

Keep all 19 rule-based anomaly detectors and add Isolation Forest (unsupervised ML) to discover unknown patterns the rules can't catch.

---

## Quick Decision Matrix

| Factor | Status | Implication |
|--------|--------|-------------|
| Labeled anomaly data? | ❌ None | Cannot use supervised ML (XGBoost) |
| Data volume | ✅ 32K+ records | Sufficient for unsupervised ML |
| Rules working? | ✅ Yes (19 types) | Keep all rules, don't replace |
| Missing anomalies? | ⚠️ Likely | ML can discover unknown patterns |
| False positives? | ⚠️ Unknown | Need monitoring first |
| Interpretability critical? | ✅ Yes (campus security) | Rules must stay for explanations |

---

## Recommended Approach

### Phase 1: Isolation Forest (Months 1-3) - $50K investment
**What:** Add unsupervised ML to discover unknown anomaly patterns
**Algorithm:** Isolation Forest (scikit-learn)
**Why:** No labeled data available, fast, discovers novel patterns
**Risk:** Low (rules still run as primary detection)
**Expected ROI:** Discover 3-10 new anomaly types rules can't catch

### Phase 2: LSTM Autoencoder (Months 4-6) - $40K investment
**What:** Add temporal pattern detection
**Algorithm:** LSTM Autoencoder (TensorFlow)
**Why:** Detect gradual behavioral shifts over time
**Risk:** Medium (requires GPU, more complex)
**Expected ROI:** 10-20% false positive reduction

### Phase 3: Supervised XGBoost (Months 7+) - Conditional
**What:** Alert prioritization system
**Algorithm:** XGBoost classifier
**Requirement:** Security team must label 500-1000 historical anomalies
**Risk:** High (depends on labeling effort)
**Expected ROI:** 30-50% false positive reduction

---

## Why NOT Replace Rules?

1. **No labeled data** - Can't train supervised classifiers without ground truth
2. **Interpretability required** - Security team must explain alerts to students/faculty
3. **Rules are comprehensive** - 19 anomaly types covering policy violations well
4. **Low risk** - Hybrid approach ensures no regressions
5. **Legal defensibility** - Rules provide clear policy violation evidence

---

## ML Algorithms Evaluated

| Algorithm | Viable? | Rationale |
|-----------|---------|-----------|
| **XGBoost (Supervised)** | ❌ No | Requires labeled data (none available) |
| **Isolation Forest** | ✅ YES | Discovers unknown patterns, no labels needed |
| **One-Class SVM** | ⚠️ Maybe | Slower than Isolation Forest, less effective |
| **Local Outlier Factor** | ❌ No | Too slow for real-time (100-500ms latency) |
| **LSTM Autoencoder** | ✅ YES | Phase 2 - detects temporal anomalies |
| **Prophet (Time-Series)** | ⚠️ Limited | Only for zone occupancy, not entity behavior |
| **ARIMA** | ❌ No | Prophet/LSTM are better for this use case |
| **VAE / GAN** | ❌ No | Dataset too small (need 100K+ records) |

---

## Key Statistics

**Current System:**
- 19 rule-based anomaly types (7 system-level + 12 entity-level)
- 100% interpretable, deterministic
- No false positive rate tracking (monitoring gap)

**Available Data:**
- 32,456 card swipe records
- 32,690 WiFi association logs
- Lab bookings, CCTV frames
- ❌ ZERO labeled anomalies

**ML Feasibility:**
- ✅ Sufficient data for unsupervised learning
- ❌ Insufficient labels for supervised learning
- ✅ Multi-modal data enables rich features

---

## Implementation Timeline

```
Month 1-3: Phase 1 - Isolation Forest
├─ Week 1-2: Feature engineering
├─ Week 3: Train model + API integration
└─ Week 4-12: Validation & tuning

Month 4-6: Phase 2 - LSTM Autoencoder (if Phase 1 succeeds)
├─ Week 1: Prepare sequential data
├─ Week 2-3: Train LSTM autoencoder
└─ Week 4-8: Validation & comparison

Month 7+: Phase 3 - Supervised XGBoost (conditional on labels)
├─ Requires 500-1000 labeled anomalies
├─ Security team labeling campaign
└─ Train XGBoost for alert prioritization
```

---

## Cost-Benefit Analysis

### Costs
- **Implementation:** $50K (Phase 1), $40K (Phase 2), $30K (Phase 3)
- **Operational:** $15-20K/year (monitoring, retraining, GPU)
- **Total Year 1:** $120K implementation + $20K operational = **$140K**

### Benefits
- Discover 5-20 novel anomaly types rules can't detect
- Reduce false positives by 30-50% (Phase 3)
- Save 5 hours/week in anomaly triage (20% time savings)
- Early detection of emerging security threats (risk mitigation)

### ROI
- **Positive if:** ML discovers ≥5 high-impact anomalies in Year 1
- **Break-even:** 10-15 hours/week saved in security operations
- **Risk-adjusted ROI:** 2-3x investment over 2 years

---

## Success Metrics

### Phase 1 KPIs
- ✅ Discover ≥3 novel anomaly types in first 2 months
- ✅ False positive rate <20%
- ✅ Inference latency <50ms per event
- ✅ 30-50% overlap with rule-based anomalies

### Phase 2 KPIs
- ✅ Detect ≥5 temporal anomaly patterns
- ✅ 10-20% false positive reduction vs Phase 1
- ✅ Inference latency <100ms per sequence

### Phase 3 KPIs (conditional)
- ✅ 500-1000 labeled anomalies collected
- ✅ XGBoost test accuracy >85%
- ✅ 30-50% false positive reduction
- ✅ 20% reduction in time to triage alerts

---

## Risk Assessment

### High Risks
- ❌ High false positive rate → **Mitigation:** Start with low contamination (5%), tune based on feedback
- ❌ Security team alert fatigue → **Mitigation:** Anomaly prioritization (Phase 3)

### Medium Risks
- ⚠️ Model drift over time → **Mitigation:** Weekly retraining, drift monitoring
- ⚠️ Interpretability challenges → **Mitigation:** Hybrid explanations (ML flags, rules explain)

### Low Risks
- ✅ Insufficient data → 32K records sufficient for unsupervised ML
- ✅ Budget overruns → Phased approach, validate ROI before next phase
- ✅ ML misses critical anomalies → Rules always run as primary detection

---

## Decision Criteria

### ✅ Proceed with Phase 1 if:
- Security team commits to reviewing ML anomalies for 3 months
- Data engineering capacity available (120 hours)
- Budget approved for $50K + $20K/year operational cost

### ❌ Abort if:
- False positive rate >50% after tuning (Week 8)
- No novel anomalies discovered after 2 months
- Security team overwhelmed by alert volume

---

## Hybrid Architecture

```
┌──────────────────────────────────────────────┐
│         ANOMALY DETECTION SYSTEM             │
├──────────────────────────────────────────────┤
│                                              │
│  ┌─────────────────┐  ┌──────────────────┐ │
│  │  RULE-BASED     │  │  ML-BASED        │ │
│  │  (19 types)     │  │  (Isolation      │ │
│  │                 │  │   Forest)        │ │
│  │  Always Runs    │  │  Discovers New   │ │
│  │  High Precision │  │  Patterns        │ │
│  └────────┬────────┘  └────────┬─────────┘ │
│           │                    │            │
│           └──────┬─────────────┘            │
│                  │                          │
│          ┌───────▼────────┐                │
│          │  DEDUPLICATE & │                │
│          │  MERGE ALERTS  │                │
│          └───────┬────────┘                │
│                  │                          │
│          ┌───────▼────────┐                │
│          │  PRIORITIZE    │                │
│          │  (ML Score +   │                │
│          │   Severity)    │                │
│          └───────┬────────┘                │
│                  │                          │
│          ┌───────▼────────┐                │
│          │  SECURITY TEAM │                │
│          │  DASHBOARD     │                │
│          └────────────────┘                │
└──────────────────────────────────────────────┘
```

---

## Next Steps

1. **Week 1:** Present analysis to security team + engineering leadership
2. **Week 2:** Get approval for Phase 1 budget ($50K)
3. **Week 3-4:** Feature engineering + Isolation Forest training
4. **Week 5-12:** Validation, tuning, security team feedback loop
5. **Month 4:** Phase 1 retrospective → decide on Phase 2

---

## Recommended Reading

Full analysis: `/Users/dinokage/dev/fazri-analyzer/docs/ANOMALY_DETECTION_ML_EVALUATION.md`

Key sections:
- Section 3: ML Algorithm Evaluation (detailed comparison)
- Section 5: Implementation Plan (code examples)
- Section 7: Cost-Benefit Analysis
- Section 12: Appendix (production code samples)

---

**Contact:** AI Engineer Agent
**Date:** 2026-03-15
**Status:** Ready for stakeholder review
