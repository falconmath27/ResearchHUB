"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "../../lib/api";
import styles from "./page.module.css";

type Mode = "register" | "login";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setIsSubmitting(true);

    try {
      if (mode === "register") {
        const registrationResponse = await fetch(`${API_BASE_URL}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
        });

        if (!registrationResponse.ok) {
          const details = await registrationResponse.json();
          throw new Error(details.detail ?? "Could not register this account.");
        }
      }

      const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!loginResponse.ok) {
        const details = await loginResponse.json();
        throw new Error(details.detail ?? "Invalid email or password.");
      }

      const token = (await loginResponse.json()).access_token;
      window.localStorage.setItem("researchhub_access_token", token);
      router.push("/projects");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not complete authentication.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <p className={styles.eyebrow}>RESEARCHHUB / ACCOUNT</p>
        <h1>{mode === "register" ? "Create an account" : "Welcome back"}</h1>
        <p className={styles.intro}>{mode === "register" ? "Create an account to own and collaborate on research projects." : "Sign in to access your research projects."}</p>

        <div className={styles.modeButtons}>
          <button className={mode === "register" ? styles.active : ""} onClick={() => setMode("register")} type="button">Register</button>
          <button className={mode === "login" ? styles.active : ""} onClick={() => setMode("login")} type="button">Sign in</button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          {mode === "register" && <label>Name<input value={name} onChange={(event) => setName(event.target.value)} minLength={2} required /></label>}
          <label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></label>
          <label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} type="password" required /></label>
          <button className={styles.submit} disabled={isSubmitting} type="submit">{isSubmitting ? "Please wait..." : mode === "register" ? "Create account" : "Sign in"}</button>
        </form>

        {errorMessage && <p className={styles.error}>{errorMessage}</p>}
        <Link className={styles.backLink} href="/projects">Back to projects</Link>
      </section>
    </main>
  );
}
