"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/api";
import styles from "./page.module.css";

type Project = {
  id: number;
  title: string;
  summary: string;
  field: string;
  tags: string[];
  visibility: "private" | "public";
};

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    async function loadProject() {
      try {
        const response = await apiFetch(`/projects/${projectId}`);

        if (response.status === 401 || response.status === 403) {
          setErrorMessage("Sign in to view this project.");
          return;
        }

        if (response.status === 404) {
          setErrorMessage("This project does not exist.");
          return;
        }

        if (!response.ok) {
          throw new Error("The API could not load this project.");
        }

        setProject(await response.json());
      } catch {
        setErrorMessage("Could not reach the ResearchHub API. Check that it is running on port 8000.");
      } finally {
        setIsLoading(false);
      }
    }

    loadProject();
  }, [projectId]);

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!project) return;

    setIsSaving(true);
    setErrorMessage("");
    const formData = new FormData(event.currentTarget);
    const updatedProject = {
      title: String(formData.get("title")),
      summary: String(formData.get("summary")),
      field: String(formData.get("field")),
      tags: String(formData.get("tags")).split(",").map((tag) => tag.trim()).filter(Boolean),
      visibility: String(formData.get("visibility")) as "private" | "public",
    };

    try {
      const response = await apiFetch(`/projects/${projectId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedProject),
      });

      if (!response.ok) {
        const details = await response.json();
        throw new Error(details.detail?.[0]?.msg ?? "Could not update the project.");
      }

      setProject(await response.json());
      setIsEditing(false);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update the project.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this project permanently?")) return;

    setIsDeleting(true);
    setErrorMessage("");

    try {
      const response = await apiFetch(`/projects/${projectId}`, { method: "DELETE" });

      if (!response.ok) throw new Error("Could not delete the project.");

      router.push("/projects");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not delete the project.");
      setIsDeleting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <Link className={styles.backLink} href="/projects">Back to projects</Link>

        {isLoading && <p className={styles.notice}>Loading project...</p>}
        {errorMessage && <p className={`${styles.notice} ${styles.error}`}>{errorMessage}</p>}

        {project && !isEditing && (
          <article>
            <header className={styles.header}>
              <div>
                <p className={styles.eyebrow}>{project.field}</p>
                <h1>{project.title}</h1>
              </div>
              <div className={styles.actions}>
                <span className={styles.visibility}>{project.visibility}</span>
                <button className={styles.editButton} onClick={() => setIsEditing(true)} type="button">Edit</button>
                <button className={styles.deleteButton} disabled={isDeleting} onClick={handleDelete} type="button">{isDeleting ? "Deleting..." : "Delete"}</button>
              </div>
            </header>
            <section className={styles.section}>
              <h2>Research summary</h2>
              <p>{project.summary}</p>
            </section>
            <section className={styles.section}>
              <h2>Tags</h2>
              {project.tags.length > 0 ? <div className={styles.tags}>{project.tags.map((tag) => <em key={tag}>{tag}</em>)}</div> : <p>No tags have been added.</p>}
            </section>
            <section className={styles.section}>
              <h2>Workspace</h2>
              <p><Link href={`/projects/${projectId}/notes`}>Research notes</Link> &nbsp; | &nbsp; <Link href={`/projects/${projectId}/tasks`}>Task board</Link> &nbsp; | &nbsp; <Link href={`/projects/${projectId}/sources`}>Source library</Link> &nbsp; | &nbsp; <Link href={`/projects/${projectId}/discussion`}>Team discussion</Link></p>
            </section>
          </article>
        )}

        {project && isEditing && (
          <form className={styles.form} onSubmit={handleUpdate}>
            <header className={styles.header}>
              <div>
                <p className={styles.eyebrow}>EDIT PROJECT</p>
                <h1>{project.title}</h1>
              </div>
            </header>
            <label>Project title<input defaultValue={project.title} maxLength={120} minLength={3} name="title" required /></label>
            <label>Summary<textarea defaultValue={project.summary} maxLength={1000} minLength={10} name="summary" required /></label>
            <label>Research field<input defaultValue={project.field} maxLength={80} minLength={2} name="field" required /></label>
            <label>Tags <small>Separate tags with commas.</small><input defaultValue={project.tags.join(", ")} name="tags" /></label>
            <label>Visibility
              <select defaultValue={project.visibility} name="visibility">
                <option value="private">Private</option>
                <option value="public">Public</option>
              </select>
            </label>
            <div className={styles.formActions}>
              <button className={styles.editButton} disabled={isSaving} type="submit">{isSaving ? "Saving..." : "Save changes"}</button>
              <button className={styles.cancelButton} onClick={() => setIsEditing(false)} type="button">Cancel</button>
            </div>
          </form>
        )}
      </section>
    </main>
  );
}
