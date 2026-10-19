"""
Lumi DICOM — DICOM C-FIND SCU smoke test
Copyright © 2026 Lumi DICOM. All rights reserved.

Query the running MWL SCP as a modality would, to verify the worklist
is actually served over DICOM.
"""

from pydicom.dataset import Dataset
from pynetdicom import AE
from pynetdicom.sop_class import ModalityWorklistInformationFind


def main():
    ae = AE(ae_title="MODALITY_CT01")
    ae.add_requested_context(ModalityWorklistInformationFind)

    assoc = ae.associate("127.0.0.1", 11112, ae_title="LUMI_DICOM")
    if not assoc.is_established:
        print("FAILED: could not associate with LUMI_DICOM MWL SCP")
        return

    print("Associated with LUMI_DICOM MWL SCP (AE: MODALITY_CT01)")

    query = Dataset()
    query.QueryRetrieveLevel = "WORKLIST"
    query.ScheduledProcedureStepStartDate = "20261018"
    query.Modality = "CT"
    query.PatientName = ""
    query.PatientID = ""

    matches = []
    for status, identifier in assoc.send_c_find(
        query, ModalityWorklistInformationFind
    ):
        if status and status.Status in (0xFF00, 0xFF01) and identifier:
            matches.append(identifier)

    print(f"C-FIND matches: {len(matches)}")
    for m in matches:
        print("  ---")
        print(f"  AccessionNumber : {getattr(m, 'AccessionNumber', '?')}")
        print(f"  PatientID       : {getattr(m, 'PatientID', '?')}")
        print(f"  PatientName     : {getattr(m, 'PatientName', '?')}")
        print(f"  Modality        : {getattr(m, 'Modality', '?')}")
        print(f"  StationAETitle  : {getattr(m, 'ScheduledStationAETitle', '?')}")
        print(f"  StudyDesc       : {getattr(m, 'StudyDescription', '?')}")

    assoc.release()
    print("Association released.")


if __name__ == "__main__":
    main()
