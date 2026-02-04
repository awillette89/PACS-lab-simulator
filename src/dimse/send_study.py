import argparse
import requests
import json
import os
from pynetdicom import AE, StoragePresentationContexts
from pynetdicom.sop_class import Verification
from pydicom import dcmread
from ..export_to_fhir import dicom_to_fhir_imagingstudy, get_study_metadata_from_orthanc
from datetime import datetime

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", help="Path to DICOM file")
    p.add_argument("--peer", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4242)
    p.add_argument("--called-aet", default="ORTHANC")
    p.add_argument("--calling-aet", default="PYNETDICOM")
    args = p.parse_args()

    ae = AE(ae_title=args.calling_aet)
    ae.requested_contexts = StoragePresentationContexts
    ae.add_requested_context(Verification)

    assoc = ae.associate(args.peer, args.port, ae_title=args.called_aet)
    if not assoc.is_established:
        raise SystemExit("Association failed")
    
    status = assoc.send_c_echo()
    if not getattr(status, "Status", None) == 0x0000:
        raise SystemExit(f"C-ECHO failed: {getattr(status,'Status',None)}")
    
    ds = dcmread(args.path)
    st = assoc.send_c_store(ds)
    print(f"C-STORE status: 0x{getattr(st,'Status',0):04X}")

    assoc.release()

    # FHIR Export
    try:
        # Get StudyInstanceUID from the DICOM dataset we just sent
        study_uid = ds.StudyInstanceUID
        print(f"Exporting FHIR for StudyInstanceUID: {study_uid}")

        metadata = get_study_metadata_from_orthanc(study_uid)
        imaging_study = dicom_to_fhir_imagingstudy(metadata)
        
        fhir_json = imaging_study.model_dump()
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()  # e.g. "2026-02-04T13:22:12Z"
                return super().default(obj)

        output_path = f"data/fhir/{study_uid}.ImagingStudy.json"
        os.makedirs("data/fhir", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(
                fhir_json,
                f,
                indent=2,
                cls=DateTimeEncoder
            )
        print(f"FHIR ImagingStudy saved to {output_path}")
        
    except AttributeError as e:
        print(f"FHIR export skipped - could not read StudyInstanceUID: {e}")
    except Exception as e:
        import traceback
        print(f"FHIR export failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()