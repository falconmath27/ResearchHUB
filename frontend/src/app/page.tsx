"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "../lib/api";
import styles from "./page.module.css";

type Project = {
  id: number;
  title: string;
  summary: string;
  field: string;
  tags: string[];
  visibility: "private" | "public";
};

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadProjects() {
      try {
        const response = await apiFetch("/projects");

        if (response.status === 401 || response.status === 403) {
          throw new Error("Sign in to view your private research workspace.");
        }
        if (!response.ok) {
          throw new Error("Could not load projects from the ResearchHub API.");
        }

        const loadedProjects = await response.json();
        if (!cancelled) setProjects(loadedProjects);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : "Could not load your workspace.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadProjects();
    return () => { cancelled = true; };
  }, []);

  return (
    <main className={styles.page}>
      <header className={styles.topbar}>
        <Link className={styles.brand} href="/">✣ Research<span>HUB</span></Link>
        <nav className={styles.nav} aria-label="Main navigation">
          <Link href="/projects">Projects</Link>
          <Link href="/projects/new">Create project</Link>
          <Link href="/auth">Account</Link>
        </nav>
      </header>

      <section className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>LIVE RESEARCH WORKSPACE</p>
          <h1>Organize the work behind your research.</h1>
          <p className={styles.lede}>Projects, research notes, task boards, and team discussion are connected to the ResearchHub API and protected by project membership.</p>
        </div>
        <div className={styles.heroActions}>
          <Link className={styles.primaryAction} href="/projects/new">Create project</Link>
          <Link className={styles.secondaryAction} href="/projects">View all projects</Link>
        </div>
      </section>

      <section className={styles.capabilities} aria-label="ResearchHub capabilities">
        <article><span>01</span><h2>Research notes</h2><p>Capture decisions, findings, and working ideas with author accountability.</p></article>
        <article><span>02</span><h2>Task board</h2><p>Assign project work and move it through a shared research workflow.</p></article>
        <article><span>03</span><h2>Team discussion</h2><p>Keep blockers, updates, and decisions alongside the project they belong to.</p></article>
      </section>

      <section className={styles.projectsSection}>
        <header className={styles.sectionHeader}>
          <div><p className={styles.eyebrow}>YOUR PROJECTS</p><h2>Active research</h2></div>
          <Link href="/projects">Open project library</Link>
        </header>

        {isLoading && <p className={styles.notice}>Loading your workspace...</p>}
        {errorMessage && <div className={`${styles.notice} ${styles.error}`}><p>{errorMessage}</p><Link href="/auth">Sign in or create an account</Link></div>}
        {!isLoading && !errorMessage && projects.length === 0 && <p className={styles.notice}>No projects yet. Create the first shared research workspace.</p>}

        <div className={styles.projectGrid}>
          {projects.map((project) => (
            <article className={styles.projectCard} key={project.id}>
              <div className={styles.cardMeta}><span>{project.field}</span><small>{project.visibility}</small></div>
              <h3>{project.title}</h3>
              <p>{project.summary}</p>
              <div className={styles.tags}>{project.tags.slice(0, 3).map((tag) => <em key={tag}>{tag}</em>)}</div>
              <nav className={styles.workspaceNav} aria-label={`${project.title} workspace`}>
                <Link href={`/projects/${project.id}`}>Overview</Link>
                <Link href={`/projects/${project.id}/notes`}>Notes</Link>
                <Link href={`/projects/${project.id}/tasks`}>Tasks</Link>
                <Link href={`/projects/${project.id}/sources`}>Sources</Link>
                <Link href={`/projects/${project.id}/discussion`}>Discussion</Link>
              </nav>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
