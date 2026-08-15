import type { Asset } from '@/types';

/**
 * Preview URL derivation — a display concern only. The backend records the
 * canonical file URL for each asset; some of those files are not things a
 * browser can put in an <img> (Wikimedia returns PDFs and DjVu scans for many
 * queries), and the image ones are full-size originals that can run to
 * megabytes.
 *
 * MediaWiki's Special:FilePath endpoint solves both: given a file name and a
 * width it returns a rasterised, resized preview — page 1 for PDFs, a PNG
 * render for SVGs, a scaled copy for photos. We never rewrite the asset's own
 * URL, only what we show in the card.
 */

const WIKIMEDIA_UPLOAD_HOST = 'upload.wikimedia.org';
const PREVIEW_WIDTH = 640;

/** Extensions a browser will happily render in an <img>. */
const RENDERABLE = /\.(jpe?g|png|gif|webp|avif|svg)(\?|$)/i;

/** File types we know need rasterising before they can be shown. */
const DOCUMENT_LIKE = /\.(pdf|djvu|tiff?|ogv|webm|ogg|mp4)(\?|$)/i;

function wikimediaFileName(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl);
    if (url.hostname !== WIKIMEDIA_UPLOAD_HOST) return null;
    // .../commons/4/43/Some_File.pdf  →  Some_File.pdf
    const last = url.pathname.split('/').filter(Boolean).pop();
    return last ? decodeURIComponent(last) : null;
  } catch {
    return null;
  }
}

/**
 * Best preview URL for an asset, or null when there is nothing showable.
 * Falls back to the raw thumbnail/asset URL for non-Wikimedia providers.
 */
export function previewUrl(asset: Asset): string | null {
  const raw = asset.thumbnail_url || asset.asset_url;
  if (!raw) return null;

  const fileName = wikimediaFileName(raw);
  if (fileName) {
    return `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(
      fileName
    )}?width=${PREVIEW_WIDTH}`;
  }

  return raw;
}

/**
 * The real file type behind the asset, for the badge on the card — an editor
 * needs to know a "match" is a PDF scan before they click through.
 */
export function fileKind(asset: Asset): string | null {
  const raw = asset.asset_url || asset.thumbnail_url || '';
  const match = raw.match(/\.([a-z0-9]{2,5})(\?|$)/i);
  if (!match) return null;
  const ext = match[1].toUpperCase();
  if (RENDERABLE.test(raw)) return ext;
  if (DOCUMENT_LIKE.test(raw)) return ext;
  return ext;
}

/** True when the underlying file is a document/video rather than a picture. */
export function isDocumentAsset(asset: Asset): boolean {
  return DOCUMENT_LIKE.test(asset.asset_url || '');
}
