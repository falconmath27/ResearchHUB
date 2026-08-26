"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";
import styles from "./page.module.css";

type Project = {
  id: number;
  title: string;
  summary: string;
  field: string;
  tags: string[];
  visibility: "private" | "public";
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [visibility, setVisibility] = useState<"all" | "private" | "public">("all");
  const [tag, setTag] = useState("");

  useEffect(() => {
    async function loadProjects() {
      try {
        setIsLoading(true);
        setErrorMessage("");
        const searchParams = new URLSearchParams();
        if (visibility !== "all") searchParams.set("visibility", visibility);
        if (tag.trim()) searchParams.set("tag", tag.trim());
        const response = await apiFetch(`/projects${searchParams.size ? `?${searchParams}` : ""}`);

        if (response.status === 401 || response.status === 403) {
          setErrorMessage("Sign in to view your projects.");
          return;
        }

        if (!response.ok) {
          throw new Error("The API could not load projects.");
        }

        setProjects(await response.json());
      } catch {
        setErrorMessage("Could not reach the ResearchHub API. Check that it is running on port 8000.");
      } finally {
        setIsLoading(false);
      }
    }

    loadProjects();
  }, [tag, visibility]);

  return (
    <main className={styles.page}>
      <section className={styles.content}>
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>RESEARCHHUB / PROJECTS</p>
            <h1>Your projects</h1>
            <p>Projects saved through the ResearchHub API.</p>
          </div>
          <div className={styles.headerLinks}>
            <Link className={styles.signInLink} href="/auth">Sign in</Link>
            <Link className={styles.createLink} href="/projects/new">Create project</Link>
          </div>
        </header>

        <section className={styles.filters} aria-label="Project filters">
          <label>Visibility
            <select value={visibility} onChange={(event) => setVisibility(event.target.value as "all" | "private" | "public")}>
              <option value="all">All projects</option>
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
          </label>
          <label>Tag
            <input value={tag} onChange={(event) => setTag(event.target.value)} placeholder="Filter by an exact tag" />
          </label>
        </section>

        {isLoading && <p className={styles.notice}>Loading projects...</p>}
        {errorMessage && <p className={`${styles.notice} ${styles.error}`}>{errorMessage}</p>}
        {!isLoading && !errorMessage && projects.length === 0 && <p className={styles.notice}>No projects match these filters.</p>}

        <div className={styles.grid}>
          {projects.map((project) => (
            <Link className={styles.card} href={`/projects/${project.id}`} key={project.id}>
              <div className={styles.cardHeader}>
                <span>{project.field}</span>
                <small>{project.visibility}</small>
              </div>
              <h2>{project.title}</h2>
              <p>{project.summary}</p>
              {project.tags.length > 0 && <div className={styles.tags}>{project.tags.map((tag) => <em key={tag}>{tag}</em>)}</div>}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
