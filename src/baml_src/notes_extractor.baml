// Extract medication information and side effects experienced by the patient from nurse's notes
class Medication {
  name string
  date string @description("Date format is YYYY-MM-DD")
  dosage string @description("Dosage of the medication")
  frequency string @description("Frequency of the medication")
}

class PatientInfo {
  patient_id string
  medication Medication
  side_effects string[] @description("Do not list intensity or frequency of the side effect")
}

function ExtractMedicationInfo(notes: string) -> PatientInfo[] {
  client OpenRouterGPT41
  prompt #"
    Extract the medication information from the following nurse's notes.
    Include only documented side effects, not vital signs or observations.
    When listing side effects, do not describe its intensity or frequency.
    ONLY list the name of the side effect.

    {{ ctx.output_format }}

    {{ _.role("user") }} {{ notes }}
  "#
}

test TestWithVitalSigns {
  functions [ExtractMedicationInfo]
  args {
    notes #"
      Patient ID: X7F3Q
      Date: October 12 2024
      Medication: Ramipril 5mg PO daily
      Side Effects: Patient reports persistent dry cough and occasional dizziness when standing.
      BP reduced from 156/92 to 132/78. No angioedema observed. Will continue to monitor for hypotension.
    "#
  }
}

test TestNegation {
  functions [ExtractMedicationInfo]
  args {
    notes #"
      Patient ID: L9M2W
      Date: November 3 2024
      Medication: Metformin 1000mg BID
      Side Effects: Reports mild nausea after morning dose. Denies diarrhea. Blood sugar levels stable.
    "#
  }
}