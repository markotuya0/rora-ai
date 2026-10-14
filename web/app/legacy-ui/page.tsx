const LEGACY_URL = process.env.NEXT_PUBLIC_LEGACY_UI_URL ?? "http://localhost:8501";

export default function LegacyUiPage() {
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-4 p-4">
      <h1 className="text-base font-semibold">Legacy interface</h1>
      <p className="text-sm text-muted">
        The Streamlit UI is kept for one release while the dashboard replaces it. It still works, but it has no guided
        view and no keyboard shortcuts. The dashboard is the supported interface.
      </p>
      <a
        href={LEGACY_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="min-h-11 rounded-panel border border-edge px-4 py-2 text-center text-sm font-medium text-ink"
      >
        Open the legacy UI
      </a>
      <a href="/dashboard" className="min-h-11 rounded-panel bg-accent px-4 py-2 text-center text-sm font-semibold text-surface">
        Go to the dashboard
      </a>
    </main>
  );
}
