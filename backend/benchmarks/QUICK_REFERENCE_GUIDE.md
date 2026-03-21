# ML Algorithm Quick Reference Guide
## Location Prediction - Campus Security System

---

## TL;DR - Executive Summary

**Current State**: RandomForest with **17.21ms P95 latency** (FAILS <10ms requirement)

**Recommended Action**: **Switch to LightGBM**
- 57x faster (0.30ms P95)
- 62% smaller models
- Only 10% accuracy loss
- 3-4 week migration timeline

---

## At-a-Glance Comparison

### Speed Champion: NeuralNetwork_Small
- **0.04ms P95 latency** (386x faster than RandomForest)
- 23,170 predictions/sec throughput
- 2.3MB total memory (99% smaller)
- Trade-off: 17% accuracy loss

### Balance Champion: LightGBM (RECOMMENDED)
- **0.30ms P95 latency** (57x faster than RandomForest)
- 3,461 predictions/sec throughput
- 129.7MB total memory (62% smaller)
- Trade-off: Only 10% accuracy loss

### Accuracy Champion: RandomForest (Current Baseline)
- **17.21ms P95 latency** (FAILS <10ms SLA)
- Only 68 predictions/sec throughput
- 346.9MB total memory
- Trade-off: Unacceptable latency performance

---

## Performance Metrics Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INFERENCE LATENCY (P95)                          │
│                    Lower is Better                                  │
├─────────────────────────────────────────────────────────────────────┤
│ LogisticRegression   ▏0.02ms                                       │
│ NeuralNetwork_Small  ▏0.04ms                                       │
│ NeuralNetwork_Large  ▏0.05ms                                       │
│ LightGBM             ▎0.30ms   ← RECOMMENDED                       │
│ GradientBoosting     ▎0.42ms                                       │
│ XGBoost              ▎0.47ms                                       │
│ RandomForest         █████████████████▌17.21ms  ← CURRENT (SLOW!)  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        ACCURACY                                     │
│                    Higher is Better                                 │
├─────────────────────────────────────────────────────────────────────┤
│ RandomForest         ████████████████████████████████████▌40.7%     │
│ GradientBoosting     ███████████████████████████████▌36.7%          │
│ LightGBM             ███████████████████████████████▌36.6%          │
│ XGBoost              ██████████████████████████████▌35.8%           │
│ NeuralNetwork_Small  █████████████████████████████▏33.7%            │
│ NeuralNetwork_Large  ████████████████████████████▌33.4%             │
│ LogisticRegression   ███████████████████████▏27.7%                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    MODEL SIZE (31 models)                           │
│                    Lower is Better                                  │
├─────────────────────────────────────────────────────────────────────┤
│ LogisticRegression   ▏0.04 MB                                      │
│ NeuralNetwork_Small  ▏2.3 MB    ← SMALLEST                         │
│ NeuralNetwork_Large  ▏8.4 MB                                       │
│ LightGBM             ████▌129.7 MB  ← RECOMMENDED                   │
│ GradientBoosting     █████▍151.8 MB                                │
│ XGBoost              ██████▌187.3 MB                                │
│ RandomForest         ████████████▌346.9 MB  ← CURRENT (LARGE!)     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    THROUGHPUT                                       │
│                    Higher is Better                                 │
├─────────────────────────────────────────────────────────────────────┤
│ LogisticRegression   ████████████████████████████████▌62,713 p/s    │
│ NeuralNetwork_Small  ███████████████████████▌23,170 p/s ← FASTEST   │
│ NeuralNetwork_Large  ██████████████████████▌21,226 p/s              │
│ LightGBM             ███▌3,461 p/s   ← RECOMMENDED                  │
│ GradientBoosting     ██▌2,732 p/s                                   │
│ XGBoost              ██▍2,563 p/s                                   │
│ RandomForest         ▏68 p/s        ← CURRENT (SLOW!)               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Decision Matrix

### Choose LightGBM if:
- ✓ You need <10ms latency (gets 0.30ms)
- ✓ Accuracy is important (only 10% loss)
- ✓ You have 130MB memory available
- ✓ Training time <5 seconds is acceptable
- ✓ You want production-proven technology

**Confidence Level**: HIGH
**Migration Effort**: LOW
**Risk Level**: LOW

---

### Choose NeuralNetwork_Small if:
- ✓ You need ultra-low latency (<1ms)
- ✓ Memory is extremely limited (<10MB total)
- ✓ High throughput (20k+ pred/sec) required
- ✓ Fast retraining (<10s) is critical
- ✓ 17% accuracy loss is acceptable

**Confidence Level**: MEDIUM
**Migration Effort**: MODERATE
**Risk Level**: MEDIUM (accuracy impact)

---

### Choose GradientBoosting if:
- ✓ You prefer sklearn ecosystem (no new dependencies)
- ✓ LightGBM/XGBoost installation is problematic
- ✓ Latency <1ms is sufficient
- ✓ Memory constraint is <200MB

**Confidence Level**: MEDIUM
**Migration Effort**: LOW
**Risk Level**: LOW

---

### Keep RandomForest if:
- ✓ Accuracy loss is completely unacceptable
- ✓ You can tolerate 17ms latency (FAILS SLA)
- ✓ You can tolerate 347MB memory usage
- ✓ You can tolerate 68 pred/sec throughput
- ✗ **NOT RECOMMENDED** - fails performance requirements

**Confidence Level**: LOW
**Migration Effort**: ZERO
**Risk Level**: HIGH (SLA violation)

---

## Performance Improvement Calculator

### If you switch from RandomForest to LightGBM:

**Latency Improvement**:
- Before: 17.21ms P95
- After: 0.30ms P95
- Improvement: **98.3% faster**
- Impact: Meets <10ms SLA requirement

**Memory Savings**:
- Before: 346.9 MB
- After: 129.7 MB
- Savings: **217.2 MB (62% reduction)**
- Impact: Can run on smaller instances

**Throughput Improvement**:
- Before: 68 predictions/sec
- After: 3,461 predictions/sec
- Improvement: **51x higher throughput**
- Impact: Same hardware handles 51x more load

**Accuracy Trade-off**:
- Before: 40.7%
- After: 36.6%
- Loss: **-4.1 percentage points (10% relative)**
- Impact: Acceptable for 98% latency improvement

---

### If you switch from RandomForest to NeuralNetwork_Small:

**Latency Improvement**:
- Before: 17.21ms P95
- After: 0.04ms P95
- Improvement: **99.7% faster (386x)**
- Impact: Real-time capable, meets strictest SLA

**Memory Savings**:
- Before: 346.9 MB
- After: 2.3 MB
- Savings: **344.6 MB (99% reduction)**
- Impact: Can deploy on embedded devices

**Throughput Improvement**:
- Before: 68 predictions/sec
- After: 23,170 predictions/sec
- Improvement: **341x higher throughput**
- Impact: Can serve millions of predictions/day

**Accuracy Trade-off**:
- Before: 40.7%
- After: 33.7%
- Loss: **-7 percentage points (17% relative)**
- Impact: Significant accuracy loss, evaluate against business requirements

---

## Common Questions

### Q: Why is RandomForest so slow?
**A**: The benchmark shows 17.21ms P95 latency, which is 20x slower than the expected ~0.84ms. This indicates:
1. Potential implementation issue in the inference pipeline
2. Over-parameterization (100 trees, depth 10 may be excessive)
3. Inefficient model loading or prediction batching

**Action Required**: Profile the inference code to identify bottlenecks.

---

### Q: Which algorithm has the best accuracy?
**A**: RandomForest has the highest accuracy (40.7%) but FAILS latency requirements.

Among algorithms that meet SLA:
1. GradientBoosting: 36.7%
2. LightGBM: 36.6%  ← **RECOMMENDED**
3. XGBoost: 35.8%

The 4.1 percentage point accuracy loss (10% relative) is acceptable trade-off for 98% latency improvement.

---

### Q: What's the fastest algorithm?
**A**: LogisticRegression (0.02ms P95, 62,713 pred/sec) but has poor accuracy (27.7%).

Among accurate algorithms:
1. NeuralNetwork_Small: 0.04ms P95, 33.7% accuracy
2. NeuralNetwork_Large: 0.05ms P95, 33.4% accuracy
3. LightGBM: 0.30ms P95, 36.6% accuracy ← **BEST BALANCE**

---

### Q: What uses the least memory?
**A**: LogisticRegression (0.04MB total) but has poor accuracy (27.7%).

Among accurate algorithms:
1. NeuralNetwork_Small: 2.3 MB total ← **EXTREMELY EFFICIENT**
2. NeuralNetwork_Large: 8.4 MB total
3. LightGBM: 129.7 MB total ← **REASONABLE**

---

### Q: How long does training take?
**A**: For all 31 models:
- RandomForest: 3.3 seconds ← **FASTEST**
- NeuralNetwork_Large: 5.6 seconds
- NeuralNetwork_Small: 7.5 seconds
- LogisticRegression: 35.6 seconds
- XGBoost: 81.1 seconds (1.4 minutes)
- LightGBM: 137.4 seconds (2.3 minutes) ← **ACCEPTABLE**
- GradientBoosting: 140.4 seconds (2.3 minutes)

All algorithms train fast enough for daily or hourly retraining.

---

### Q: What's the migration effort?
**A**:
- **LightGBM**: LOW (1-2 weeks)
  - Same scikit-learn API
  - Drop-in replacement in training pipeline
  - Minimal code changes

- **NeuralNetwork**: MODERATE (2-3 weeks)
  - Different API (sklearn.neural_network)
  - Requires hyperparameter tuning
  - Integration testing needed

- **GradientBoosting**: LOW (1 week)
  - Already in scikit-learn
  - No new dependencies
  - Simple code changes

---

## Migration Checklist

### Phase 1: Validation (Week 1)
- [ ] Install LightGBM: `pip install lightgbm`
- [ ] Train LightGBM models for 5 entities
- [ ] Compare predictions with RandomForest on test data
- [ ] Measure latency on production-like load
- [ ] Validate accuracy on real data (target: >35%)

### Phase 2: Testing (Week 2)
- [ ] Set up A/B testing infrastructure
- [ ] Deploy LightGBM for 10% of entities
- [ ] Monitor latency (target: <1ms P95)
- [ ] Monitor accuracy (target: >35%)
- [ ] Collect user feedback
- [ ] Measure business impact

### Phase 3: Rollout (Week 3-4)
- [ ] Scale to 50% of entities
- [ ] Monitor for 3 days
- [ ] Scale to 100% if metrics are positive
- [ ] Update documentation
- [ ] Archive RandomForest models as backup
- [ ] Remove RandomForest dependency (optional)

### Phase 4: Optimization (Week 4+)
- [ ] Hyperparameter tuning (learning_rate, num_leaves)
- [ ] Feature engineering improvements
- [ ] Explore ensemble methods
- [ ] Set up automated retraining pipeline
- [ ] Document performance baselines

---

## Risk Mitigation

### Risk: Accuracy degradation impacts user experience
**Mitigation**:
- Run A/B test with 10% traffic before full rollout
- Measure user satisfaction metrics
- Define rollback criteria (e.g., >15% accuracy drop)
- Keep RandomForest models as backup for 30 days

### Risk: LightGBM introduces deployment complexity
**Mitigation**:
- Test on development environment first
- Verify cross-platform compatibility (Docker)
- Document installation steps
- Add health checks for model loading

### Risk: Performance benefits don't materialize in production
**Mitigation**:
- Benchmark on production hardware
- Test with realistic load patterns
- Monitor P95/P99 latency with alerting
- Have rollback plan ready

---

## Success Metrics

Track these metrics to validate migration success:

### Performance Metrics
- **P95 Latency**: Target <1ms (currently 17.21ms)
- **P99 Latency**: Target <2ms
- **Throughput**: Target >1,000 pred/sec (currently 68)
- **Memory Usage**: Target <150MB (currently 347MB)

### Business Metrics
- **Prediction Accuracy**: Target >35% (currently 40.7%)
- **User Satisfaction**: Maintain or improve current levels
- **API Response Time**: Overall API latency improvement
- **Cost Savings**: Reduced infrastructure costs from memory savings

### Operational Metrics
- **Training Time**: Target <5 minutes for all 31 models
- **Model Update Frequency**: Enable hourly retraining
- **Deployment Success Rate**: >95% successful deployments
- **Incident Rate**: Zero production incidents from migration

---

## Support & Resources

**Benchmark Results**: `/backend/benchmarks/benchmark_results_20260315_161751.json`

**Detailed Report**: `/backend/benchmarks/benchmark_report_20260315_161751.txt`

**Executive Summary**: `/backend/benchmarks/ALGORITHM_COMPARISON_EXECUTIVE_SUMMARY.md`

**Benchmark Script**: `/backend/scripts/benchmark_algorithms_synthetic.py`

**Re-run Benchmark**:
```bash
cd /Users/dinokage/dev/fazri-analyzer/backend
source anal/bin/activate
python scripts/benchmark_algorithms_synthetic.py
```

**Contact**: Performance Benchmarker Agent

---

**Last Updated**: March 15, 2026
**Next Review**: After production migration (4 weeks)
