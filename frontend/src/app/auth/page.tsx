"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "../../lib/api";
import styles from "./page.module.css";

type Mode = "register" | "login" | "forgot" | "recover";
type ApiError = { detail?: string | Array<{ msg?: string }> };

async function responseError(response: Response, fallback: string) {
  try {
    const body = await response.json() as ApiError;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      const messages = body.detail.flatMap((item) => item.msg ? [item.msg] : []);
      if (messages.length > 0) return messages.join(" ");
    }
  } catch {
    // Use the stable fallback when the API did not return JSON.
  }
  return fallback;
}

const headings: Record<Mode, { title: string; intro: string }> = {
  register: { title: "Create an account", intro: "Create an account to own and collaborate on research projects." },
  login: { title: "Welcome back", intro: "Sign in to access your research projects." },
  forgot: { title: "Reset your password", intro: "Enter your account email. The response stays the same whether or not an account exists." },
  recover: { title: "Request account recovery", intro: "If you cannot remember or access your account email, send a request for manual support review." },
};

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberedEmail, setRememberedEmail] = useState("");
  const [details, setDetails] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [developmentResetUrl, setDevelopmentResetUrl] = useState<string | null>(null);
  const [showRegisterPrompt, setShowRegisterPrompt] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function changeMode(nextMode: Mode) {
    setMode(nextMode);
    setErrorMessage("");
    setSuccessMessage("");
    setDevelopmentResetUrl(null);
    setShowRegisterPrompt(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");
    setDevelopmentResetUrl(null);
    setShowRegisterPrompt(false);
    setIsSubmitting(true);

    try {
      if (mode === "forgot") {
        const response = await fetch(`${API_BASE_URL}/auth/password-reset/request`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }),
        });
        if (!response.ok) {
          if (response.status === 404) setShowRegisterPrompt(true);
          throw new Error(await responseError(response, "Could not request a reset."));
        }
        const result = await response.json();
        setSuccessMessage(result.message);
        setDevelopmentResetUrl(result.development_reset_url);
        return;
      }

      if (mode === "recover") {
        const response = await fetch(`${API_BASE_URL}/auth/account-recovery`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, contact_email: email, remembered_email: rememberedEmail || null, details }),
        });
        if (!response.ok) throw new Error(await responseError(response, "Could not create a recovery request."));
        const result = await response.json();
        setSuccessMessage(`${result.message} Reference: ${result.reference_code}`);
        return;
      }

      if (mode === "register") {
        const registrationResponse = await fetch(`${API_BASE_URL}/auth/register`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, email, password }),
        });
        if (!registrationResponse.ok) throw new Error(await responseError(registrationResponse, "Could not register this account."));
      }

      const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
      });
      if (!loginResponse.ok) throw new Error(await responseError(loginResponse, "Invalid email or password."));

      const token = (await loginResponse.json()).access_token;
      window.localStorage.setItem("researchhub_access_token", token);
      router.push("/projects");
    } catch (error) {
      setErrorMessage(error instanceof TypeError
        ? "Could not reach the ResearchHub API. Confirm the backend is running on port 8000."
        : error instanceof Error ? error.message : "Could not complete authentication.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const heading = headings[mode];
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <p className={styles.eyebrow}>RESEARCHHUB / ACCOUNT</p>
        <h1>{heading.title}</h1>
        <p className={styles.intro}>{heading.intro}</p>

        {(mode === "register" || mode === "login") && <div className={styles.modeButtons}>
          <button aria-pressed={mode === "register"} className={mode === "register" ? styles.active : ""} onClick={() => changeMode("register")} type="button">Register</button>
          <button aria-pressed={mode === "login"} className={mode === "login" ? styles.active : ""} onClick={() => changeMode("login")} type="button">Sign in</button>
        </div>}

        <form className={styles.form} onSubmit={handleSubmit}>
          {(mode === "register" || mode === "recover") && <label>Name<input autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} required /></label>}
          <label>{mode === "recover" ? "Contact email" : "Email"}<input autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></label>
          {mode === "recover" && <label>Remembered account email (optional)<input value={rememberedEmail} onChange={(event) => setRememberedEmail(event.target.value)} type="email" /></label>}
          {(mode === "register" || mode === "login") && <label>Password<input autoComplete={mode === "register" ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} type="password" required /></label>}
          {mode === "recover" && <label>Recovery details<textarea value={details} onChange={(event) => setDetails(event.target.value)} minLength={20} maxLength={2000} placeholder="Explain what you remember about the account and why you cannot access it." required /></label>}
          <button className={styles.submit} disabled={isSubmitting} type="submit">{isSubmitting ? "Please wait..." : mode === "register" ? "Create account" : mode === "login" ? "Sign in" : mode === "forgot" ? "Request reset" : "Send recovery request"}</button>
        </form>

        {errorMessage && <p className={styles.error}>{errorMessage}</p>}
        {showRegisterPrompt && <button className={styles.registerPrompt} onClick={() => changeMode("register")} type="button">Register a new account</button>}
        {successMessage && <p className={styles.success}>{successMessage}</p>}
        {developmentResetUrl && <Link className={styles.resetLink} href={developmentResetUrl.replace("http://localhost:3000", "")}>Open local reset page</Link>}

        <div className={styles.recoveryLinks}>
          {mode === "login" && <button onClick={() => changeMode("forgot")} type="button">Forgot password?</button>}
          {(mode === "login" || mode === "forgot") && <button onClick={() => changeMode("recover")} type="button">Can&apos;t remember or access your email?</button>}
          {(mode === "forgot" || mode === "recover") && <button onClick={() => changeMode("login")} type="button">Back to sign in</button>}
        </div>
        <Link className={styles.backLink} href="/projects">Back to projects</Link>
      </section>
    </main>
  );
}
