from pathlib import Path

app_name = "energy-theft-detection"
app_entrypoint = "energy_theft_detection.backend.app:app"
app_slug = "energy_theft_detection"
api_prefix = "/api"
dist_dir = Path(__file__).parent / "__dist__"