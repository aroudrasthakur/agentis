"use client";

import { useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import type { AgentDescriptionFormat } from "@/lib/api";

export function AgentDescriptionEditor({
  description,
  descriptionFormat,
  saving,
  onSave,
}: {
  description: string;
  descriptionFormat: AgentDescriptionFormat;
  saving?: boolean;
  onSave: (description: string, format: AgentDescriptionFormat) => void;
}) {
  const [text, setText] = useState(description);
  const [format, setFormat] = useState<AgentDescriptionFormat>(descriptionFormat);
  const [mode, setMode] = useState<"write" | "preview">("write");
  const fileRef = useRef<HTMLInputElement>(null);

  const dirty = text !== description || format !== descriptionFormat;

  const preview = useMemo(() => text.trim(), [text]);

  function importFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const content = String(reader.result ?? "");
      setText(content);
      const name = file.name.toLowerCase();
      if (name.endsWith(".md") || name.endsWith(".markdown") || file.type.includes("markdown")) {
        setFormat("markdown");
      }
      setMode("write");
    };
    reader.readAsText(file);
  }

  return (
    <section className="rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-xl text-ink">About this agent</h2>
          <p className="mt-1 max-w-2xl text-sm text-ink/55">
            Explain what this agent does, who it is for, and how it should behave. Plain text and
            Markdown are both supported — upload a <code className="text-xs">.md</code> file or
            type directly.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={mode === "write" ? "default" : "outline"}
            onClick={() => setMode("write")}
          >
            Write
          </Button>
          <Button
            type="button"
            size="sm"
            variant={mode === "preview" ? "default" : "outline"}
            onClick={() => setMode("preview")}
          >
            Preview
          </Button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <span className="text-xs uppercase tracking-[0.14em] text-ink/40">Format</span>
        <label className="inline-flex items-center gap-2 text-sm text-ink/70">
          <input
            type="radio"
            name="description-format"
            checked={format === "plain"}
            onChange={() => setFormat("plain")}
          />
          Plain text
        </label>
        <label className="inline-flex items-center gap-2 text-sm text-ink/70">
          <input
            type="radio"
            name="description-format"
            checked={format === "markdown"}
            onChange={() => setFormat("markdown")}
          />
          Markdown
        </label>
        <input
          ref={fileRef}
          type="file"
          accept=".md,.markdown,.txt,text/markdown,text/plain"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) importFile(file);
            event.target.value = "";
          }}
        />
        <Button type="button" size="sm" variant="outline" onClick={() => fileRef.current?.click()}>
          Upload Markdown file
        </Button>
      </div>

      {mode === "write" ? (
        <textarea
          className="mt-4 min-h-[200px] w-full rounded-md border border-ink/15 bg-surface/80 px-3 py-3 text-sm text-ink placeholder:text-ink/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal"
          placeholder={
            format === "markdown"
              ? "## Purpose\n\nDescribe this agent in Markdown…"
              : "Describe what this agent does and when to use it…"
          }
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
      ) : (
        <div className="prose prose-sm prose-invert mt-4 max-w-none rounded-md border border-ink/10 bg-ink/5 px-4 py-4 text-ink/80">
          {preview ? (
            format === "markdown" ? (
              <ReactMarkdown>{preview}</ReactMarkdown>
            ) : (
              <p className="whitespace-pre-wrap">{preview}</p>
            )
          ) : (
            <p className="text-ink/45">Nothing to preview yet.</p>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          variant="teal"
          disabled={saving || !dirty}
          onClick={() => onSave(text.trim(), format)}
        >
          {saving ? "Saving…" : "Save description"}
        </Button>
      </div>
    </section>
  );
}
