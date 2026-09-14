"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "../../../../lib/api";
import styles from "./page.module.css";

type Note = { id: number; title: string; content: string; updated_at: string };
type NoteVersion = {
  id: number;
  version: number;
  title: string;
  content: string;
  editor_name: string | null;
  created_at: string;
};

export default function ProjectNotesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [notes, setNotes] = useState<Note[]>([]);
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [historyNoteId, setHistoryNoteId] = useState<number | null>(null);
  const [versionsByNote, setVersionsByNote] = useState<Record<number, NoteVersion[]>>({});
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [message, setMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  async function loadNotes() {
    const response = await apiFetch(`/projects/${projectId}/notes`);
    if (!response.ok) throw new Error("Could not load notes. Sign in and confirm project access.");
    setNotes(await response.json());
  }

  useEffect(() => {
    void loadNotes().catch((error) => {
      setMessage(error instanceof Error ? error.message : "Could not load notes.");
    });
  }, [projectId]);

  function resetForm() {
    setEditingNote(null);
    setTitle("");
    setContent("");
  }

  function beginEdit(note: Note) {
    setEditingNote(note);
    setTitle(note.title);
    setContent(note.content);
  }

  async function saveNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setIsSaving(true);
    const path = editingNote
      ? `/projects/${projectId}/notes/${editingNote.id}`
      : `/projects/${projectId}/notes`;

    try {
      const response = await apiFetch(path, {
        method: editingNote ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, content }),
      });
      if (!response.ok) {
        setMessage("Could not save this note. You need author, editor, or owner permission.");
        return;
      }
      resetForm();
      await loadNotes();
    } catch {
      setMessage("Could not reach the ResearchHub API while saving this note.");
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteNote(noteId: number) {
    if (!confirm("Delete this note permanently, including its version history?")) return;
    const response = await apiFetch(`/projects/${projectId}/notes/${noteId}`, { method: "DELETE" });
    if (!response.ok) {
      setMessage("Could not delete this note.");
      return;
    }
    if (historyNoteId === noteId) setHistoryNoteId(null);
    await loadNotes();
  }

  async function loadHistory(noteId: number) {
    setMessage("");
    setIsLoadingHistory(true);
    try {
      const response = await apiFetch(`/projects/${projectId}/notes/${noteId}/versions`);
      if (!response.ok) {
        setMessage("Could not load this note's version history.");
        return;
      }
      const versions = await response.json();
      setVersionsByNote((currentVersions) => ({
        ...currentVersions,
        [noteId]: versions,
      }));
      setHistoryNoteId(noteId);
    } catch {
      setMessage("Could not reach the ResearchHub API while loading history.");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function restoreVersion(noteId: number, version: NoteVersion) {
    if (!confirm(`Restore Version ${version.version}? This creates a new latest version and keeps every existing one.`)) return;
    const response = await apiFetch(
      `/projects/${projectId}/notes/${noteId}/versions/${version.id}/restore`,
      { method: "POST" },
    );
    if (!response.ok) {
      setMessage("Could not restore this version. You need author, editor, or owner permission.");
      return;
    }
    await Promise.all([loadNotes(), loadHistory(noteId)]);
  }

  return (
    <main className={styles.page}>
      <section className={styles.shell}>
        <Link className={styles.back} href={`/projects/${projectId}`}>Back to project</Link>
        <header>
          <p>RESEARCHHUB / NOTES</p>
          <h1>Research notes</h1>
          <span>Capture findings with a complete, restorable decision trail.</span>
        </header>

        <form className={styles.form} onSubmit={saveNote}>
          <h2>{editingNote ? "Edit note" : "New note"}</h2>
          <input value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} maxLength={200} placeholder="Note title" required />
          <textarea value={content} onChange={(event) => setContent(event.target.value)} minLength={1} maxLength={10000} placeholder="Write the research note..." required />
          <div><button disabled={isSaving} type="submit">{isSaving ? "Saving..." : editingNote ? "Save changes" : "Create note"}</button>{editingNote && <button className={styles.cancel} onClick={resetForm} type="button">Cancel</button>}</div>
        </form>

        {message && <p className={styles.message}>{message}</p>}
        <div className={styles.list}>
          {notes.map((note) => (
            <article key={note.id}>
              <div className={styles.noteHeading}><small>UPDATED {new Date(note.updated_at).toLocaleDateString()}</small><button className={styles.historyButton} disabled={isLoadingHistory} onClick={() => historyNoteId === note.id ? setHistoryNoteId(null) : void loadHistory(note.id)} type="button">{historyNoteId === note.id ? "Hide history" : "Version history"}</button></div>
              <h2>{note.title}</h2>
              <p>{note.content}</p>
              <div><button onClick={() => beginEdit(note)} type="button">Edit</button><button className={styles.danger} onClick={() => void deleteNote(note.id)} type="button">Delete</button></div>
              {historyNoteId === note.id && <section className={styles.history}>
                <div className={styles.historyTitle}><h3>Version history</h3><span>Restoring creates a new latest version.</span></div>
                {versionsByNote[note.id]?.map((version) => <article className={styles.versionCard} key={version.id}><div><strong>Version {version.version}</strong><small>{new Date(version.created_at).toLocaleString()} by {version.editor_name ?? "Former member"}</small></div><h4>{version.title}</h4><p>{version.content}</p><button onClick={() => void restoreVersion(note.id, version)} type="button">Restore this version</button></article>)}
              </section>}
            </article>
          ))}
        </div>
        {!message && notes.length === 0 && <p className={styles.empty}>No notes yet. Start the project record with the first one.</p>}
      </section>
    </main>
  );
}
