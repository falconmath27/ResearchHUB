"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "../../../../lib/api";
import styles from "./page.module.css";

type Note = { id: number; title: string; content: string; updated_at: string };

export default function ProjectNotesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [notes, setNotes] = useState<Note[]>([]);
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [message, setMessage] = useState("");

  async function loadNotes() {
    const response = await apiFetch(`/projects/${projectId}/notes`);
    if (!response.ok) throw new Error("Could not load notes. Sign in and confirm project access.");
    setNotes(await response.json());
  }

  useEffect(() => {
    let cancelled = false;

    async function fetchNotes() {
      try {
        const response = await apiFetch(`/projects/${projectId}/notes`);
        if (!response.ok) throw new Error("Could not load notes. Sign in and confirm project access.");
        if (!cancelled) setNotes(await response.json());
      } catch (error) {
        if (!cancelled) setMessage(error instanceof Error ? error.message : "Could not load notes.");
      }
    }

    void fetchNotes();
    return () => { cancelled = true; };
  }, [projectId]);

  async function saveNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    const path = editingNote ? `/projects/${projectId}/notes/${editingNote.id}` : `/projects/${projectId}/notes`;
    const response = await apiFetch(path, {
      method: editingNote ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content }),
    });
    if (!response.ok) { setMessage("Could not save this note. You need author, editor, or owner permission."); return; }
    setTitle(""); setContent(""); setEditingNote(null); await loadNotes();
  }

  async function deleteNote(noteId: number) {
    if (!confirm("Delete this note permanently?")) return;
    const response = await apiFetch(`/projects/${projectId}/notes/${noteId}`, { method: "DELETE" });
    if (!response.ok) { setMessage("Could not delete this note."); return; }
    await loadNotes();
  }

  function beginEdit(note: Note) { setEditingNote(note); setTitle(note.title); setContent(note.content); }

  return <main className={styles.page}><section className={styles.shell}>
    <Link className={styles.back} href={`/projects/${projectId}`}>Back to project</Link>
    <header><p>RESEARCHHUB / NOTES</p><h1>Research notes</h1><span>Capture decisions, findings, and working ideas.</span></header>
    <form className={styles.form} onSubmit={saveNote}>
      <h2>{editingNote ? "Edit note" : "New note"}</h2>
      <input value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} maxLength={200} placeholder="Note title" required />
      <textarea value={content} onChange={(event) => setContent(event.target.value)} minLength={1} maxLength={10000} placeholder="Write the research note..." required />
      <div><button type="submit">{editingNote ? "Save changes" : "Create note"}</button>{editingNote && <button className={styles.cancel} onClick={() => { setEditingNote(null); setTitle(""); setContent(""); }} type="button">Cancel</button>}</div>
    </form>
    {message && <p className={styles.message}>{message}</p>}
    <div className={styles.list}>{notes.map((note) => <article key={note.id}><small>UPDATED {new Date(note.updated_at).toLocaleDateString()}</small><h2>{note.title}</h2><p>{note.content}</p><div><button onClick={() => beginEdit(note)} type="button">Edit</button><button className={styles.danger} onClick={() => deleteNote(note.id)} type="button">Delete</button></div></article>)}</div>
    {!message && notes.length === 0 && <p className={styles.empty}>No notes yet. Start the project record with the first one.</p>}
  </section></main>;
}
