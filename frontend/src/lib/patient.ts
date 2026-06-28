export interface PatientProfile {
  patientId: string;
  phoneNumber: string;
  displayName: string;
}

const STORAGE_KEY = "joy_patient";

export function getStoredPatient(): PatientProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as PatientProfile;
  } catch {
    return null;
  }
}

export function storePatient(patient: PatientProfile): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(patient));
}

export function clearPatient(): void {
  localStorage.removeItem(STORAGE_KEY);
}
