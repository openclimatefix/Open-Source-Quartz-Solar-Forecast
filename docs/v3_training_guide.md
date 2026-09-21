# V3 LightGBM Model - Training Guide

This guide explains how to train the V3 LightGBM solar forecast model using real data from HuggingFace.

## Prerequisites

### 1. Install Dependencies

```bash
pip install lightgbm huggingface_hub datasets
```

### 2. HuggingFace Authentication

The UK PV dataset requires authentication. Follow these steps:

1. **Create HuggingFace Account**: 
   - Go to [https://huggingface.co/join](https://huggingface.co/join)
   - Sign up for a free account

2. **Request Dataset Access**:
   - Navigate to [openclimatefix/uk_pv](https://huggingface.co/datasets/openclimatefix/uk_pv)
   - Click "Request Access" (may require accepting terms)

3. **Generate Access Token**:
   - Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Click "New token"
   - Name: `ocf-training`
   - Type: `Read` (or `Write` if you want to upload models)
   - Copy the token

4. **Authenticate CLI**:
   ```bash
   huggingface-cli login
   # Paste your token when prompted
   ```

## Training

### Quick Training (Development)

For fast iteration during development, use sampling:

```bash
cd open-source-quartz-solar-forecast

# Sample 20 sites, 7 days each
python scripts/train_v3_model.py --sample-sites 20 --sample-days 7
```

This takes ~5-10 minutes and produces a usable model for testing.

### Full Training (Production)

For the best model quality:

```bash
# Train on 500 sites, full year
python scripts/train_v3_model.py --sample-sites 500 --sample-days 365
```

This takes ~1-2 hours depending on your hardware.

### Training Output

After training, you'll find:
- `quartz_solar_forecast/models/model-v3.0.pkl` - Trained model
- Console output with MAE and normalized MAE metrics

## Benchmarking

To compare against v1 and v2 models, run the eval script:

```bash
# Run evaluation on all models
python scripts/run_eval.py --models v1 v2 v3
```

## Troubleshooting

### "Dataset not found" Error
- Ensure you've requested access to `openclimatefix/uk_pv`
- Re-run `huggingface-cli login`

### Memory Issues
- Reduce `--sample-sites` to 50 or less
- Use a machine with more RAM

### Training Metrics

Good expected values:
- **MAE**: 0.1-0.3 kW (depends on system size)
- **Normalized MAE**: 5-15%

## Next Steps

After training a model with real data:
1. Run benchmarks to compare with v1/v2
2. Update the PR with results
3. Consider hyperparameter tuning
