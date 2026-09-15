# Replit Face Engine Test

This Replit entrypoint hosts only the testing UI. LivePortrait and CodeFormer
still run in the configured RunPod GPU endpoint, so Replit does not need CUDA
or model weights.

## Replit setup

1. Import this repository into Replit.
2. Install the small UI dependency set:

   ```text
   pip install -r requirements-replit.txt
   ```

3. Add these Replit Secrets:

   ```text
   RUNPOD_API_KEY=...
   RUNPOD_ENDPOINT_FACE=...
   ```

4. Run the app. Replit uses `.replit` and exposes the Streamlit port.

Upload a face image and driving audio, then click **Generate test video**.
The UI accepts the handler's returned MP4 data URI directly, so no public
storage bucket is required for this test path.