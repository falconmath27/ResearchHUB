"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

const API_URL = "http://localhost:8000/projects";

export default function NewProjectPage() {
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [field, setField] = useState("");
  const [tags, setTags] = useState("");
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setStatus("idle");
    setErrorMessage("");

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          summary,
          field,
          tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
          visibility,
        }),
      });

      if (!response.ok) {
        const details = await response.json();
        setErrorMessage(details.detail?.[0]?.msg ?? "Could not create project.");
        setStatus("error");
        return;
      }

      setTitle("");
      setSummary("");
      setField("");
      setTags("");
      setVisibility("private");
      setStatus("success");
    } catch {
      setErrorMessage("Could not reach the ResearchHub API. Check that it is running on port 8000.");
      setStatus("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <p className={styles.eyebrow}>RESEARCHHUB / PROJECTS</p>
        <h1>Create a project</h1>
        <p className={styles.intro}>Add the basic project details. ResearchHub will save them to the local database.</p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label>
            Project title
            <input value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} maxLength={120} required />
          </label>
          <label>
            Summary
            <textarea value={summary} onChange={(event) => setSummary(event.target.value)} minLength={10} maxLength={1000} required />
          </label>
          <label>
            Research field
            <input value={field} onChange={(event) => setField(event.target.value)} minLength={2} maxLength={80} required />
          </label>
          <label>
            Tags <small>Separate tags with commas.</small>
            <input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="climate, policy, data" />
          </label>
          <label>
            Visibility
            <select value={visibility} onChange={(event) => setVisibility(event.target.value as "private" | "public")}>
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
          </label>
          <button className={styles.submit} disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating..." : "Create project"}
          </button>
        </form>

        {status === "success" && <p className={`${styles.message} ${styles.success}`}>Project created successfully.</p>}
        {status === "error" && <p className={`${styles.message} ${styles.error}`}>{errorMessage}</p>}
        <Link className={styles.backLink} href="/projects">View all projects</Link>
      </section>
    </main>
  );
}
