import subprocess, sys, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(pyfile, *args):
    cmd = [sys.executable, str(ROOT / pyfile), *map(str, args)]
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    # 1) Ensure a WL exists
    run("src/admin/create_wl_file.py")

    # 2) Prove MWL is queryable
    run("src/dimse/find_mwl_verbose.py")

    # 3) “Acquire” a DICOM from MWL
    run("src/dimse/acquire_from_mwl.py")

    # 4) Send it to Orthanc (pick newest CT_* file)
    files = sorted(glob.glob(str(ROOT / "data" / "samples" / "CT_*.dcm")), key=os.path.getmtime)
    if not files:
        raise SystemExit("No CT_* DICOM found in data/samples/")
    run("src/dimse/send_study.py", files[-1])

    print("\nDone. Open http://localhost:8042/ (orthanc/orthanc) to view the study.")

if __name__ == "__main__":
    main()
