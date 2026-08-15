const MAP: Record<string, { color: string; label: string }> = {
  completed: { color: 'bg-sage', label: 'Complete' },
  processing: { color: 'bg-ochre', label: 'Processing' },
  failed: { color: 'bg-rust', label: 'Failed' },
  draft: { color: 'bg-faint', label: 'Not started' },
  pending: { color: 'bg-faint', label: 'Queued' },
};

export default function StatusDot({ status }: { status: string }) {
  const s = MAP[status] ?? { color: 'bg-faint', label: status };
  return (
    <span className="inline-flex shrink-0 items-center" title={s.label}>
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${s.color}`} />
      <span className="sr-only">{s.label}</span>
    </span>
  );
}
