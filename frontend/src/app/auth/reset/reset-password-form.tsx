"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { API_BASE_URL } from "../../../lib/api";
import styles from "../page.module.css";

export default function ResetPasswordForm({ initialToken }: { initialToken: string }) {
  const [token, setToken] = useState(initialToken);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (initialToken) window.history.replaceState({}, "", "/auth/reset");
  }, [initialToken]);

  async function submitReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    if (password !== confirmation) {
      setMessage("Passwords do not match.");
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token, new_password: password }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "Could not reset the password.");
      }
      setIsSuccess(true);
      setMessage("Password updated. Existing sessions were signed out; sign in with your new password.");
    } catch (error) {
      setMessage(error instanceof TypeError ? "Could not reach the ResearchHub API." : error instanceof Error ? error.message : "Could not reset the password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return <main className={styles.page}>
    <section className={styles.card}>
      <p className={styles.eyebrow}>RESEARCHHUB / PASSWORD RESET</p>
      <h1>Choose a new password</h1>
      <p className={styles.intro}>Reset links expire after 30 minutes and work only once.</p>
      {!isSuccess && <form className={styles.form} onSubmit={submitReset}>
        {!initialToken && <label>Reset token<input value={token} onChange={(event) => setToken(event.target.value)} minLength={32} required /></label>}
        <label>New password<input autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} type="password" required /></label>
        <label>Confirm new password<input autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} minLength={8} type="password" required /></label>
        <button className={styles.submit} disabled={isSubmitting} type="submit">{isSubmitting ? "Updating..." : "Reset password"}</button>
      </form>}
      {message && <p className={isSuccess ? styles.success : styles.error}>{message}</p>}
      <Link className={styles.backLink} href="/auth">Back to sign in</Link>
    </section>
  </main>;
}
