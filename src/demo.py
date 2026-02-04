import subprocess, sys, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(module_path, *args):
    # Use the venv Python if it exists, otherwise fall back
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"   # Windows path
    if venv_python.exists():
        python_exe = venv_python
    else:
        python_exe = sys.executable  # fallback to whatever is running demo.py

    cmd = [str(python_exe), "-m", module_path, *map(str, args)]
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, text=True)

def main():
    # 1) Ensure a WL exists
    run("src.admin.create_wl_file")

    # 2) Prove MWL is queryable
    run("src.dimse.find_mwl_verbose")

    # 3) “Acquire” a DICOM from MWL
    run("src.dimse.acquire_from_mwl")

    # 4) Send it to Orthanc (pick newest CT_* file)
    files = sorted(glob.glob(str(ROOT / "data" / "samples" / "CT_*.dcm")), key=os.path.getmtime)
    if not files:
        raise SystemExit("No CT_* DICOM found in data/samples/")
    run("src.dimse.send_study", files[-1])    # ← this is the important one

    print("\nDone. Open http://localhost:8042/ (orthanc/orthanc) to view the study.")

if __name__ == "__main__":
    main()