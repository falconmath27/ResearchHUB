"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "../../../../lib/api";
import styles from "./page.module.css";

type Message = {
  id: number;
  author_id: number;
  author_name: string;
  content: string;
  created_at: string;
};

export default function ProjectDiscussionPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  async function loadMessages() {
    const response = await apiFetch(`/projects/${projectId}/messages`);
    if (!response.ok) {
      throw new Error("Could not load discussion. Sign in and confirm project access.");
    }
    setMessages(await response.json());
  }

  useEffect(() => {
    let cancelled = false;

    async function fetchMessages() {
      try {
        const response = await apiFetch(`/projects/${projectId}/messages`);
        if (!response.ok) {
          throw new Error("Could not load discussion. Sign in and confirm project access.");
        }
        const loadedMessages = await response.json();
        if (!cancelled) setMessages(loadedMessages);
      } catch (error) {
        if (!cancelled) {
          setMessage(error instanceof Error ? error.message : "Could not load discussion.");
        }
      }
    }

    void fetchMessages();
    return () => { cancelled = true; };
  }, [projectId]);

  async function postMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setIsSubmitting(true);

    try {
      const response = await apiFetch(`/projects/${projectId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const details = await response.json();
        throw new Error(details.detail ?? "Could not post this message.");
      }

      setContent("");
      await loadMessages();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not post this message.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.shell}>
        <Link className={styles.back} href={`/projects/${projectId}`}>Back to project</Link>
        <header className={styles.header}>
          <p>RESEARCHHUB / DISCUSSION</p>
          <h1>Team discussion</h1>
          <span>Share decisions, blockers, and research updates with the project team.</span>
        </header>

        <form className={styles.composer} onSubmit={postMessage}>
          <label htmlFor="message-content">New message</label>
          <textarea
            id="message-content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            minLength={1}
            maxLength={4000}
            placeholder="Write an update for the project team..."
            required
          />
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Posting..." : "Post message"}
          </button>
        </form>

        {message && <p className={styles.notice}>{message}</p>}
        {messages.length === 0 && !message && <p className={styles.empty}>No messages yet. Start the discussion.</p>}

        <section className={styles.feed} aria-label="Project discussion messages">
          {messages.map((projectMessage) => (
            <article className={styles.messageCard} key={projectMessage.id}>
              <div className={styles.avatar}>{projectMessage.author_name.slice(0, 2).toUpperCase()}</div>
              <div className={styles.messageBody}>
                <header>
                  <strong>{projectMessage.author_name}</strong>
                  <time dateTime={projectMessage.created_at}>{new Date(projectMessage.created_at).toLocaleString()}</time>
                </header>
                <p>{projectMessage.content}</p>
              </div>
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
