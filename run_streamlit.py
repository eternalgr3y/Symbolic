"""
Run the Streamlit frontend for SymbolicAGI
"""
import subprocess
import sys

def main():
    """Run the Streamlit app."""
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "symbolic_agi/streamlit_app.py",
        "--server.port", "8501",
        "--server.address", "localhost"
    ])

if __name__ == "__main__":
    main()