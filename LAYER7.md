# Layer 7: Ghost Engine dashboard

Launch the dedicated Streamlit dashboard from the repository root:

```powershell
streamlit run dashboard.py
```

The dashboard provides script input, camera/lighting/atmosphere/emotion selectors, a 2x/4x upscale control, optional ambient-audio upload, six-layer progress updates, a per-render duration and ₹23 default scene estimate, plus MP4 preview/download. Override the displayed cost estimate with `ZOVIX_ESTIMATED_SCENE_COST_INR`. The value is a planning estimate within the requested ₹20–25 range; actual costs vary by provider and the dashboard does not charge credits.

Layer 1–6 credentials and runtime dependencies are still required as described in [LAYER6.md](LAYER6.md). Uploaded ambience is stored temporarily while rendering and removed afterward.
