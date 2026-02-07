from fhir.resources.imagingstudy import ImagingStudy
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.coding import Coding
import datetime
import requests
from requests.auth import HTTPBasicAuth

print("DEBUG: export_to_fhir.py module loaded successfully")

def get_study_metadata_from_orthanc(study_uid: str, orthanc_url: str = "http://localhost:8042"):
    qido_url = f"{orthanc_url}/dicom-web/studies"
    params = {
        "StudyInstanceUID": study_uid,
        "includefield": "all",
        "limit": 1
    }
    auth = HTTPBasicAuth("orthanc", "orthanc")

    try:
        response = requests.get(qido_url, params=params, auth=auth)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("DEBUG: HTTP error details:", e.response.text)            # ← Better error info
        raise

    results = response.json()
    if not results:
        raise ValueError(f"No study found for UID {study_uid}")
    return results[0]


def dicom_to_fhir_imagingstudy(dicom_json: dict, patient_ref: str = "Patient/example-patient") -> ImagingStudy:
    from fhir.resources.codeableconcept import CodeableConcept
    from fhir.resources.coding import Coding

    # Extract DICOM tags (safe .get with defaults)
    study_uid = dicom_json.get("0020000D", {}).get("Value", [None])[0]
    study_date = dicom_json.get("00080020", {}).get("Value", [None])[0]  # e.g. "20260204"
    study_time = dicom_json.get("00080030", {}).get("Value", [None])[0]  # e.g. "132212"
    modalities_str = dicom_json.get("00080061", {}).get("Value", ["CT"])[0]  # ModalitiesInStudy

    # Build started dateTime with timezone (required if time present)
    if study_date:
        year = study_date[0:4]
        month = study_date[4:6] if len(study_date) >= 6 else "01"
        day = study_date[6:8] if len(study_date) >= 8 else "01"

        if study_time and len(study_time) >= 6:
            hour = study_time[0:2]
            minute = study_time[2:4]
            second = study_time[4:6]
            started_str = f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"  # UTC timezone
        else:
            started_str = f"{year}-{month}-{day}"  # Date only (no T/time)
    else:
        # Fallback: current UTC time, no fractional seconds
        import datetime
        now = datetime.datetime.utcnow()
        started_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Modality: Wrap in CodeableConcept (required fix from earlier)
    modality_codes = []
    for mod in modalities_str.split('\\'):
        mod = mod.strip()
        if mod:
            modality_codes.append(
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://dicom.nema.org/resources/ontology/DCM",
                            code=mod,
                            display=mod  # Can map to full names later if needed
                        )
                    ]
                )
            )

    study = ImagingStudy(
        resourceType="ImagingStudy",
        status="available",
        modality=modality_codes or [CodeableConcept(coding=[Coding(code="CT")])],  # Fallback if missing
        subject=Reference(reference=patient_ref),
        started=started_str,
        identifier=[
            Identifier(
                use="official",
                system="urn:dicom:uid",
                value=f"urn:oid:{study_uid}" if study_uid else None
            )
        ],
        numberOfSeries=int(dicom_json.get("00200006", {}).get("Value", [0])[0] or 0),
        numberOfInstances=int(dicom_json.get("00200008", {}).get("Value", [0])[0] or 0),
    )

    return study