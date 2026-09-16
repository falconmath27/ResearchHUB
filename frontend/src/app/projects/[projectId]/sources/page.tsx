"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "../../../../lib/api";
import styles from "./page.module.css";

const sourceTypes = ["article", "book", "dataset", "report", "website", "other"] as const;
type SourceType = (typeof sourceTypes)[number];

type Source = {
  id: number;
  title: string;
  authors: string;
  publication_year: number | null;
  source_type: SourceType;
  url: string | null;
  doi: string | null;
  updated_at: string;
};

type Attachment = {
  id: number;
  source_id: number | null;
  original_filename: string;
  size_bytes: number;
  download_url: string;
};

type AnalysisJobStatus = "queued" | "processing" | "completed" | "failed";
type AnalysisResult = {
  stage: string;
  file_type?: string;
  page_count?: number | null;
  character_count?: number;
  word_count?: number;
  truncated?: boolean;
  text_preview?: string;
  model?: string;
  summary?: string;
  summary_passage_ids?: string[];
  findings?: { claim: string; passage_ids: string[] }[];
  limitations?: string[];
  passages?: { id: string; page: number | null; text: string }[];
};
type AnalysisJob = {
  id: number;
  attachment_id: number;
  parent_job_id: number | null;
  status: AnalysisJobStatus;
  kind: "extraction" | "ai";
  attempt: number;
  result: AnalysisResult | null;
  error_message: string | null;
};

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024 * 1024) return `${Math.max(1, Math.round(sizeBytes / 1024))} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function buildSourceQuery(filter: "all" | SourceType, search: string) {
  const params = new URLSearchParams();
  if (filter !== "all") params.set("source_type", filter);
  if (search.trim()) params.set("q", search.trim());
  const query = params.toString();
  return query ? `?${query}` : "";
}

export default function ProjectSourcesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [sources, setSources] = useState<Source[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [analysisJobs, setAnalysisJobs] = useState<AnalysisJob[]>([]);
  const [filter, setFilter] = useState<"all" | SourceType>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [publicationYear, setPublicationYear] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("article");
  const [url, setUrl] = useState("");
  const [doi, setDoi] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadingSourceId, setUploadingSourceId] = useState<number | null>(null);
  const [startingAnalysisFor, setStartingAnalysisFor] = useState<number | null>(null);

  async function loadSources(selectedFilter = filter, selectedSearch = debouncedSearch) {
    const response = await apiFetch(`/projects/${projectId}/sources${buildSourceQuery(selectedFilter, selectedSearch)}`);
    if (!response.ok) throw new Error("Could not load sources. Sign in and confirm project access.");
    setSources(await response.json());
  }

  async function loadAttachments() {
    const response = await apiFetch(`/projects/${projectId}/attachments`);
    if (!response.ok) throw new Error("Could not load source files.");
    setAttachments(await response.json());
  }

  async function loadAnalysisJobs() {
    const response = await apiFetch(`/projects/${projectId}/analysis-jobs`);
    if (!response.ok) throw new Error("Could not load analysis jobs.");
    setAnalysisJobs(await response.json());
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timeout);
  }, [search]);

  useEffect(() => {
    let cancelled = false;

    async function fetchLibrary() {
      setIsLoading(true);
      setMessage("");
      try {
        const [sourceResponse, attachmentResponse, analysisResponse] = await Promise.all([
          apiFetch(`/projects/${projectId}/sources${buildSourceQuery(filter, debouncedSearch)}`),
          apiFetch(`/projects/${projectId}/attachments`),
          apiFetch(`/projects/${projectId}/analysis-jobs`),
        ]);
        if (!sourceResponse.ok || !attachmentResponse.ok || !analysisResponse.ok) {
          throw new Error("Could not load the source library. Sign in and confirm project access.");
        }
        const [loadedSources, loadedAttachments, loadedAnalysisJobs] = await Promise.all([
          sourceResponse.json(),
          attachmentResponse.json(),
          analysisResponse.json(),
        ]);
        if (!cancelled) {
          setSources(loadedSources);
          setAttachments(loadedAttachments);
          setAnalysisJobs(loadedAnalysisJobs);
        }
      } catch (error) {
        if (!cancelled) setMessage(error instanceof Error ? error.message : "Could not load sources.");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void fetchLibrary();
    return () => { cancelled = true; };
  }, [debouncedSearch, filter, projectId]);

  const hasActiveAnalysis = analysisJobs.some((job) => job.status === "queued" || job.status === "processing");
  useEffect(() => {
    if (!hasActiveAnalysis) return;
    const interval = window.setInterval(() => {
      void apiFetch(`/projects/${projectId}/analysis-jobs`)
        .then((response) => {
          if (!response.ok) throw new Error("Could not refresh analysis status.");
          return response.json();
        })
        .then(setAnalysisJobs)
        .catch(() => setMessage("Could not refresh analysis status."));
    }, 1500);
    return () => window.clearInterval(interval);
  }, [hasActiveAnalysis, projectId]);

  function resetForm() {
    setEditingSource(null);
    setTitle("");
    setAuthors("");
    setPublicationYear("");
    setSourceType("article");
    setUrl("");
    setDoi("");
  }

  function beginEdit(source: Source) {
    setEditingSource(source);
    setTitle(source.title);
    setAuthors(source.authors);
    setPublicationYear(source.publication_year?.toString() ?? "");
    setSourceType(source.source_type);
    setUrl(source.url ?? "");
    setDoi(source.doi ?? "");
  }

  async function saveSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setIsSubmitting(true);

    try {
      const path = editingSource
        ? `/projects/${projectId}/sources/${editingSource.id}`
        : `/projects/${projectId}/sources`;
      const response = await apiFetch(path, {
        method: editingSource ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          authors,
          publication_year: publicationYear ? Number(publicationYear) : null,
          source_type: sourceType,
          url: url || null,
          doi: doi || null,
        }),
      });

      if (!response.ok) {
        if (response.status === 409) {
          setMessage("This project already contains a source with that DOI.");
        } else if (response.status === 422) {
          setMessage("Check the source details. A DOI should look like 10.1000/example.");
        } else {
          setMessage("Could not save this source. Owners and editors can manage the source library.");
        }
        return;
      }

      resetForm();
      await loadSources();
    } catch {
      setMessage("Could not reach the ResearchHub API while saving this source.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function deleteSource(sourceId: number) {
    if (!confirm("Delete this source record? Its uploaded files will stay in Project files.")) return;

    const response = await apiFetch(`/projects/${projectId}/sources/${sourceId}`, { method: "DELETE" });
    if (!response.ok) {
      setMessage("Could not delete this source.");
      return;
    }
    await Promise.all([loadSources(), loadAttachments()]);
  }

  async function uploadAttachment(sourceId: number, file: File) {
    setMessage("");
    setUploadingSourceId(sourceId);
    const body = new FormData();
    body.append("file", file);
    body.append("source_id", String(sourceId));

    try {
      const response = await apiFetch(`/projects/${projectId}/attachments`, {
        method: "POST",
        body,
      });
      if (!response.ok) {
        setMessage("Could not upload this file. Owners and editors can upload PDF, CSV, TSV, TXT, DOCX, XLSX, or JSON files up to 20 MB.");
        return;
      }
      await loadAttachments();
    } catch {
      setMessage("Could not reach the ResearchHub API while uploading the file.");
    } finally {
      setUploadingSourceId(null);
    }
  }

  async function downloadAttachment(attachment: Attachment) {
    const response = await apiFetch(attachment.download_url);
    if (!response.ok) {
      setMessage("Could not download this file. Sign in again and try once more.");
      return;
    }
    const objectUrl = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = attachment.original_filename;
    link.click();
    URL.revokeObjectURL(objectUrl);
  }

  async function deleteAttachment(attachmentId: number) {
    if (!confirm("Delete this uploaded file permanently?")) return;

    const response = await apiFetch(`/projects/${projectId}/attachments/${attachmentId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      setMessage("Could not delete this file.");
      return;
    }
    await loadAttachments();
  }

  async function startAnalysis(attachmentId: number) {
    setMessage("");
    setStartingAnalysisFor(attachmentId);
    try {
      const response = await apiFetch(
        `/projects/${projectId}/attachments/${attachmentId}/analysis-jobs`,
        { method: "POST" },
      );
      if (!response.ok) {
        setMessage(response.status === 422
          ? "Analysis currently supports PDF and TXT files only."
          : "Could not start analysis. Owners and editors can analyze source files.");
        return;
      }
      const job = await response.json();
      setAnalysisJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
      await loadAnalysisJobs();
    } catch {
      setMessage("Could not reach the ResearchHub API while starting analysis.");
    } finally {
      setStartingAnalysisFor(null);
    }
  }

  async function retryAnalysis(job: AnalysisJob) {
    setMessage("");
    setStartingAnalysisFor(job.attachment_id);
    try {
      const response = await apiFetch(
        `/projects/${projectId}/analysis-jobs/${job.id}/retry`,
        { method: "POST" },
      );
      if (!response.ok) {
        setMessage("Could not retry this analysis job.");
        return;
      }
      await loadAnalysisJobs();
    } catch {
      setMessage("Could not reach the ResearchHub API while retrying analysis.");
    } finally {
      setStartingAnalysisFor(null);
    }
  }

  async function startAiAnalysis(attachmentId: number) {
    if (!window.confirm("This sends selected passages from this private source to OpenAI for analysis. Continue?")) return;
    setMessage("");
    setStartingAnalysisFor(attachmentId);
    try {
      const response = await apiFetch(
        `/projects/${projectId}/attachments/${attachmentId}/ai-analysis-jobs`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        setMessage(body?.detail ?? "Could not start AI analysis.");
        return;
      }
      await loadAnalysisJobs();
    } catch {
      setMessage("Could not reach the ResearchHub API while starting AI analysis.");
    } finally {
      setStartingAnalysisFor(null);
    }
  }

  const attachmentsForSource = (sourceId: number) => attachments.filter(
    (attachment) => attachment.source_id === sourceId,
  );
  const projectFiles = attachments.filter((attachment) => attachment.source_id === null);
  const latestAnalysisFor = (attachmentId: number, kind: AnalysisJob["kind"]) => analysisJobs.find(
    (job) => job.attachment_id === attachmentId && job.kind === kind,
  );
  const canAnalyze = (attachment: Attachment) => /\.(pdf|txt)$/i.test(attachment.original_filename);

  return (
    <main className={styles.page}>
      <section className={styles.shell}>
        <Link className={styles.back} href={`/projects/${projectId}`}>Back to project</Link>
        <header className={styles.header}>
          <p>RESEARCHHUB / SOURCES</p>
          <h1>Source library</h1>
          <span>Collect references, then keep the working files with the evidence they support.</span>
        </header>

        <form className={styles.form} onSubmit={saveSource}>
          <h2>{editingSource ? "Edit source" : "Add source"}</h2>
          <input value={title} onChange={(event) => setTitle(event.target.value)} minLength={3} maxLength={500} placeholder="Source title" required />
          <div className={styles.twoColumns}>
            <input value={authors} onChange={(event) => setAuthors(event.target.value)} maxLength={1000} placeholder="Authors or organization" />
            <input value={publicationYear} onChange={(event) => setPublicationYear(event.target.value)} min="1" max="2100" placeholder="Publication year" type="number" />
          </div>
          <div className={styles.twoColumns}>
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value as SourceType)} aria-label="Source type">
              {sourceTypes.map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
            <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/source" type="url" />
          </div>
          <input value={doi} onChange={(event) => setDoi(event.target.value)} maxLength={255} placeholder="DOI, e.g. 10.1000/example or https://doi.org/10.1000/example" />
          <div><button disabled={isSubmitting} type="submit">{isSubmitting ? "Saving..." : editingSource ? "Save changes" : "Add source"}</button>{editingSource && <button className={styles.cancel} onClick={resetForm} type="button">Cancel</button>}</div>
        </form>

        <section className={styles.libraryHeader}>
          <h2>Project references</h2>
          <div className={styles.libraryControls}>
            <label>Search<input aria-label="Search sources" onChange={(event) => setSearch(event.target.value)} placeholder="Title, author, or DOI" type="search" value={search} /></label>
            <label>Filter by type<select value={filter} onChange={(event) => setFilter(event.target.value as "all" | SourceType)}><option value="all">All sources</option>{sourceTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
          </div>
        </section>
        {message && <p className={styles.notice}>{message}</p>}
        {isLoading && <p className={styles.empty}>Searching the source library...</p>}
        {!isLoading && !message && sources.length === 0 && <p className={styles.empty}>{search.trim() || filter !== "all" ? "No sources match this search and filter." : "No sources yet. Add the first project reference."}</p>}

        <div className={styles.sourceList}>
          {sources.map((source) => (
            <article className={styles.sourceCard} key={source.id}>
              <div className={styles.cardHeader}><span>{source.source_type}</span><small>{source.publication_year ?? "No year"}</small></div>
              <h3>{source.title}</h3>
              {source.authors && <p className={styles.authors}>{source.authors}</p>}
              {source.doi && <a href={`https://doi.org/${source.doi}`} rel="noreferrer" target="_blank">DOI: {source.doi}</a>}
              {source.url && <a href={source.url} rel="noreferrer" target="_blank">Open source</a>}
              <section className={styles.attachments}>
                <div className={styles.attachmentsHeader}><strong>Files</strong><label className={styles.uploadButton}>{uploadingSourceId === source.id ? "Uploading..." : "Upload file"}<input accept=".pdf,.csv,.tsv,.txt,.docx,.xlsx,.json" disabled={uploadingSourceId !== null} onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadAttachment(source.id, file); event.currentTarget.value = ""; }} type="file" /></label></div>
                {attachmentsForSource(source.id).length === 0 ? <p>No attached files yet.</p> : <ul>{attachmentsForSource(source.id).map((attachment) => {
                  const job = latestAnalysisFor(attachment.id, "extraction");
                  const aiJob = latestAnalysisFor(attachment.id, "ai");
                  const isActive = job?.status === "queued" || job?.status === "processing";
                  const aiActive = aiJob?.status === "queued" || aiJob?.status === "processing";
                  return <li key={attachment.id}>
                    <div className={styles.fileRow}><span><b>{attachment.original_filename}</b><small>{formatFileSize(attachment.size_bytes)}</small></span><div>{canAnalyze(attachment) && <button disabled={isActive || startingAnalysisFor === attachment.id} onClick={() => void startAnalysis(attachment.id)} type="button">{startingAnalysisFor === attachment.id ? "Starting..." : isActive ? "Preparing..." : job?.status === "completed" ? "Prepare again" : "Prepare for AI"}</button>}{job?.status === "completed" && <button disabled={aiActive || startingAnalysisFor === attachment.id} onClick={() => void startAiAnalysis(attachment.id)} type="button">{aiActive ? "Analyzing..." : "Analyze with AI"}</button>}<button onClick={() => void downloadAttachment(attachment)} type="button">Download</button><button className={styles.danger} onClick={() => void deleteAttachment(attachment.id)} type="button">Delete</button></div></div>
                    {job && <div className={`${styles.analysisResult} ${styles[job.status]}`}>
                      <div><strong>{job.status === "completed" ? "AI-ready extraction" : `Analysis ${job.status}`}</strong><small>Attempt {job.attempt}</small></div>
                      {job.result && <><p>{job.result.word_count?.toLocaleString()} words · {job.result.character_count?.toLocaleString()} characters{job.result.page_count != null ? ` · ${job.result.page_count} pages` : ""}{job.result.truncated ? " · extraction capped" : ""}</p><blockquote>{job.result.text_preview}</blockquote></>}
                      {job.error_message && <p>{job.error_message}</p>}
                      {job.status === "failed" && <button onClick={() => void retryAnalysis(job)} type="button">Retry extraction</button>}
                    </div>}
                    {aiJob && <div className={`${styles.analysisResult} ${styles[aiJob.status]}`}>
                      <div><strong>{aiJob.status === "completed" ? "AI source analysis" : `AI analysis ${aiJob.status}`}</strong><small>Attempt {aiJob.attempt}</small></div>
                      {aiJob.result?.summary && <><p>{aiJob.result.summary} <small>({aiJob.result.summary_passage_ids?.join(", ")})</small></p><ol>{aiJob.result.findings?.map((finding, index) => <li key={index}>{finding.claim} <small>({finding.passage_ids.join(", ")})</small></li>)}</ol>{Boolean(aiJob.result.limitations?.length) && <p>Limitations: {aiJob.result.limitations?.join("; ")}</p>}<details><summary>View cited evidence</summary>{aiJob.result.passages?.map((passage) => <blockquote key={passage.id}><strong>{passage.id}{passage.page ? ` · page ${passage.page}` : ""}</strong><br />{passage.text}</blockquote>)}</details><small>AI-generated; verify claims against the original source.</small></>}
                      {aiJob.error_message && <p>{aiJob.error_message}</p>}
                      {aiJob.status === "failed" && <button onClick={() => void retryAnalysis(aiJob)} type="button">Retry AI analysis</button>}
                    </div>}
                  </li>;
                })}</ul>}
              </section>
              <footer><time dateTime={source.updated_at}>Updated {new Date(source.updated_at).toLocaleDateString()}</time><div><button onClick={() => beginEdit(source)} type="button">Edit</button><button className={styles.danger} onClick={() => deleteSource(source.id)} type="button">Delete</button></div></footer>
            </article>
          ))}
        </div>

        {projectFiles.length > 0 && <section className={styles.projectFiles}><h2>Project files</h2><p>Files retained after their source record was removed.</p><ul>{projectFiles.map((attachment) => <li key={attachment.id}><span><b>{attachment.original_filename}</b><small>{formatFileSize(attachment.size_bytes)}</small></span><div><button onClick={() => void downloadAttachment(attachment)} type="button">Download</button><button className={styles.danger} onClick={() => void deleteAttachment(attachment.id)} type="button">Delete</button></div></li>)}</ul></section>}
      </section>
    </main>
  );
}
