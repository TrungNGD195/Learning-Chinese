# Step 7.6 deterministic input fixtures v1

These six run directories are hand-authored tiny fixtures for exercising the regression comparator only. They are marked `OFFLINE_TEST`, not official eligible, and are not Step 7.3/7.4/7.5 benchmark results. They contain the same two synthetic case identities in each layer and three explicit Step 7.5 holdout repeat outcomes.

Regenerate the committed comparison output from the backend directory with:

```powershell
$env:APP_ENV = 'test'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://step76.invalid/chinese_learning_test'
uv run python -c "from app.evaluation.step76.sample import generate_sample; print(generate_sample('..')['status'])"
```

The fake `.invalid` host is only a Settings parse placeholder. The fixture path makes no network or database request.
