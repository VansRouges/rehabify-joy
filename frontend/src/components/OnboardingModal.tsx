"use client";

import { FormEvent, useState } from "react";
import { registerPatient } from "@/lib/api";
import { storePatient } from "@/lib/patient";
import { JoyLogo } from "./JoyLogo";

interface OnboardingModalProps {
  onComplete: (displayName: string) => void;
}

export function OnboardingModal({ onComplete }: OnboardingModalProps) {
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await registerPatient(phone.trim(), name.trim());
      storePatient({
        patientId: result.patient_id,
        phoneNumber: result.phone_number,
        displayName: result.display_name,
      });
      onComplete(result.display_name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-joy-green/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-joy-border bg-white p-8 shadow-xl">
        <div className="mb-6 flex justify-center">
          <JoyLogo />
        </div>

        <h2 className="font-serif text-2xl font-semibold text-joy-green text-center">
          Welcome to Joy
        </h2>
        <p className="mt-2 text-center text-sm text-joy-text-muted">
          Tell us a bit about yourself before we begin. Your phone number helps us keep your
          conversations safe and personal.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="display-name" className="block text-sm font-medium text-joy-text">
              Your name
            </label>
            <input
              id="display-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Tunde"
              className="mt-1 w-full rounded-xl border border-joy-border px-4 py-2.5 text-joy-text focus:border-joy-green focus:outline-none focus:ring-2 focus:ring-joy-sage"
            />
          </div>

          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-joy-text">
              Phone number
            </label>
            <input
              id="phone"
              type="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="e.g. 08012345678"
              className="mt-1 w-full rounded-xl border border-joy-border px-4 py-2.5 text-joy-text focus:border-joy-green focus:outline-none focus:ring-2 focus:ring-joy-sage"
            />
            <p className="mt-1 text-xs text-joy-text-muted">
              Nigerian numbers accepted — with or without +234
            </p>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading || !name.trim() || !phone.trim()}
            className="w-full rounded-xl bg-joy-green py-3 text-sm font-semibold text-white transition-colors hover:bg-joy-green-hover disabled:opacity-50"
          >
            {loading ? "Setting up..." : "Start talking to Joy"}
          </button>
        </form>
      </div>
    </div>
  );
}
