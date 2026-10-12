"""Run the AI Compass Streamlit app from Replit's project Run button."""

import subprocess
import sys


if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "artifacts/ai-compass/app.py",
            "--server.port",
            "5000",
            "--server.address",
            "0.0.0.0",
        ],
        check=True,
    )
