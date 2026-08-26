"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "../../../../lib/api";
import styles from "./page.module.css";

type Status = "backlog" | "in_progress" | "in_review" | "done";
type Task = { id: number; title: string; description: string; status: Status; assignee_id: number | null };
type Member = { id: number; name: string; role: string };
const statuses: Status[] = ["backlog", "in_progress", "in_review", "done"];

export default function ProjectTasksPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<Status>("backlog");
  const [assigneeId, setAssigneeId] = useState("");
  const [message, setMessage] = useState("");

  async function loadWorkspace() {
    const [taskResponse, memberResponse] = await Promise.all([
      apiFetch(`/projects/${projectId}/tasks`), apiFetch(`/projects/${projectId}/members`),
    ]);
    if (!taskResponse.ok || !memberResponse.ok) throw new Error("Could not load tasks. Sign in and confirm project access.");
    setTasks(await taskResponse.json()); setMembers(await memberResponse.json());
  }

  useEffect(() => {
    let cancelled = false;

    async function fetchWorkspace() {
      try {
        const [taskResponse, memberResponse] = await Promise.all([
          apiFetch(`/projects/${projectId}/tasks`), apiFetch(`/projects/${projectId}/members`),
        ]);
        if (!taskResponse.ok || !memberResponse.ok) throw new Error("Could not load tasks. Sign in and confirm project access.");
        const [loadedTasks, loadedMembers] = await Promise.all([taskResponse.json(), memberResponse.json()]);
        if (!cancelled) { setTasks(loadedTasks); setMembers(loadedMembers); }
      } catch (error) {
        if (!cancelled) setMessage(error instanceof Error ? error.message : "Could not load tasks.");
      }
    }

    void fetchWorkspace();
    return () => { cancelled = true; };
  }, [projectId]);

  function resetForm() { setEditingTask(null); setTitle(""); setDescription(""); setStatus("backlog"); setAssigneeId(""); }
  function beginEdit(task: Task) { setEditingTask(task); setTitle(task.title); setDescription(task.description); setStatus(task.status); setAssigneeId(task.assignee_id?.toString() ?? ""); }

  async function saveTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setMessage("");
    const path = editingTask ? `/projects/${projectId}/tasks/${editingTask.id}` : `/projects/${projectId}/tasks`;
    const response = await apiFetch(path, { method: editingTask ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, description, status, assignee_id: assigneeId ? Number(assigneeId) : null }) });
    if (!response.ok) { setMessage("Could not save this task. Editors and owners can manage tasks."); return; }
    resetForm(); await loadWorkspace();
  }

  async function deleteTask(taskId: number) {
    if (!confirm("Delete this task permanently?")) return;
    const response = await apiFetch(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" });
    if (!response.ok) { setMessage("Could not delete this task."); return; }
    await loadWorkspace();
  }

  return <main className={styles.page}><section className={styles.shell}>
    <Link className={styles.back} href={`/projects/${projectId}`}>Back to project</Link>
    <header><p>RESEARCHHUB / TASKS</p><h1>Research task board</h1><span>Plan work, assign collaborators, and move research forward.</span></header>
    <form className={styles.form} onSubmit={saveTask}>
      <h2>{editingTask ? "Edit task" : "New task"}</h2><input value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} maxLength={200} placeholder="Task title" required />
      <textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={5000} placeholder="Describe the expected outcome" />
      <div className={styles.options}><label>Status<select value={status} onChange={(event) => setStatus(event.target.value as Status)}>{statuses.map((value) => <option key={value} value={value}>{value.replace("_", " ")}</option>)}</select></label><label>Assignee<select value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}><option value="">Unassigned</option>{members.map((member) => <option key={member.id} value={member.id}>{member.name} ({member.role})</option>)}</select></label></div>
      <div><button type="submit">{editingTask ? "Save changes" : "Create task"}</button>{editingTask && <button className={styles.cancel} onClick={resetForm} type="button">Cancel</button>}</div>
    </form>
    {message && <p className={styles.message}>{message}</p>}
    <section className={styles.board}>{statuses.map((column) => <div className={styles.column} key={column}><h2>{column.replace("_", " ")}</h2>{tasks.filter((task) => task.status === column).map((task) => <article key={task.id}><h3>{task.title}</h3><p>{task.description || "No description"}</p><small>{task.assignee_id ? `Assigned to member #${task.assignee_id}` : "Unassigned"}</small><div><button onClick={() => beginEdit(task)} type="button">Edit</button><button className={styles.danger} onClick={() => deleteTask(task.id)} type="button">Delete</button></div></article>)}</div>)}</section>
  </section></main>;
}
