import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg py-28 text-center">
      <p className="eyebrow">404</p>
      <h1 className="mt-4 text-2xl font-semibold tracking-tight text-bone">Page not found</h1>
      <p className="mt-3 text-sm leading-relaxed text-muted">
        That address does not match anything in SLAYERS.
      </p>
      <Link href="/" className="btn-ghost mt-6">
        Back to start
      </Link>
    </div>
  );
}
