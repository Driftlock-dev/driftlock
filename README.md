# DriftLock

**Lock webhook & API JSON contracts and catch breaking schema drift before it breaks production.**

Zero dependencies. Runs locally on any machine or directly inside GitHub Actions CI.

## Quick Start

```bash
pip install driftlock
driftlock snapshot examples/stripe_v1.json -o driftlock.contract.json
driftlock diff driftlock.contract.json examples/stripe_v2_drifted.json
```

Contact: driftlock.dev@gmail.com
