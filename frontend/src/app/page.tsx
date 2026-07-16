"use client";

import { useState } from "react";

export default function Home() {
  const [message, setMessage] = useState("");

  function handleGetStarted() {
    setMessage("ResearchHub is taking shape. Project workspaces arrive in Phase 1.");
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[#f8fafc] text-slate-900">
      <section className="relative isolate px-6 pt-6 pb-24 sm:px-10 lg:px-16">
        <div className="absolute inset-x-0 top-0 -z-10 h-[32rem] bg-[radial-gradient(circle_at_top_right,_#c7d2fe_0,_transparent_34%),radial-gradient(circle_at_15%_20%,_#ccfbf1_0,_transparent_26%)]" />
        <nav className="mx-auto flex max-w-6xl items-center justify-between">
          <a className="text-xl font-bold tracking-tight" href="#top">
            Research<span className="text-indigo-600">Hub</span>
          </a>
          <a className="rounded-full border border-slate-300 bg-white/80 px-4 py-2 text-sm font-medium shadow-sm transition hover:border-indigo-400 hover:text-indigo-700" href="#how-it-works">
            How it works
          </a>
        </nav>

        <div id="top" className="mx-auto grid max-w-6xl items-center gap-12 pt-20 lg:grid-cols-[1.1fr_.9fr] lg:pt-28">
          <div>
            <p className="mb-5 inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-800">
              A focused workspace for research teams
            </p>
            <h1 className="max-w-3xl text-5xl font-bold tracking-[-0.045em] text-slate-950 sm:text-6xl">
              Move research ideas forward, together.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              Bring notes, evidence, tasks, and discussion into one deliberate workspace—then use AI tools you control to understand the literature faster.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
              <button onClick={handleGetStarted} className="rounded-full bg-indigo-600 px-6 py-3 font-semibold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700">
                Get started
              </button>
              <a className="px-4 py-3 font-semibold text-slate-700 transition hover:text-indigo-700" href="#how-it-works">
                Explore the idea →
              </a>
            </div>
            <p aria-live="polite" className="mt-4 min-h-6 text-sm text-indigo-800">{message}</p>
          </div>

          <div className="rounded-3xl border border-white/70 bg-white/80 p-5 shadow-2xl shadow-indigo-950/10 backdrop-blur sm:p-7">
            <div className="flex items-center justify-between border-b border-slate-100 pb-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-600">Active project</p>
                <h2 className="mt-1 text-lg font-bold">Climate-resilient cities</h2>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Private</span>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <article className="rounded-2xl bg-slate-50 p-4"><p className="text-xs font-semibold text-slate-500">NEXT TASK</p><p className="mt-2 font-semibold">Review heat-island evidence</p><p className="mt-2 text-sm text-indigo-600">Assigned to Asha</p></article>
              <article className="rounded-2xl bg-indigo-50 p-4"><p className="text-xs font-semibold text-indigo-600">AI INSIGHT</p><p className="mt-2 font-semibold">Three gaps found</p><p className="mt-2 text-sm text-slate-600">Compare informal settlements.</p></article>
            </div>
            <div className="mt-4 rounded-2xl border border-slate-100 p-4"><p className="text-sm font-medium">Latest discussion</p><p className="mt-2 text-sm leading-6 text-slate-600">“The methodology section needs a stronger comparison group.”</p></div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="border-y border-slate-200 bg-white px-6 py-20 sm:px-10 lg:px-16">
        <div className="mx-auto max-w-6xl"><p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-600">One workspace, clear thinking</p><h2 className="mt-3 max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">Built for the research process—not code hosting.</h2>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {[['Organize', 'Keep ideas, sources, and claims connected to the project they support.'], ['Collaborate', 'Assign work, discuss decisions, and keep every contributor in context.'], ['Investigate', 'Use transparent AI analysis to surface claims, limits, and research gaps.']].map(([title, text], index) => <article key={title} className="rounded-2xl border border-slate-200 p-6"><span className="text-sm font-bold text-indigo-600">0{index + 1}</span><h3 className="mt-5 text-xl font-bold">{title}</h3><p className="mt-3 leading-7 text-slate-600">{text}</p></article>)}
          </div>
        </div>
      </section>
    </main>
  );
}
