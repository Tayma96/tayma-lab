import cfgJson from '../../site.config.json';

export const cfg = cfgJson as any;

const base = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : import.meta.env.BASE_URL + '/';

/** Site içi göreli yol: url('yazilar/x/') -> /tayma-lab/yazilar/x/ */
export function url(path = ''): string {
  return base + path.replace(/^\//, '');
}

/** Mutlak URL (canonical, OG, sitemap için) */
export function absUrl(path = ''): string {
  return new URL(url(path), cfg.siteUrl).toString();
}

export function slugify(s: string): string {
  const map: Record<string, string> = { ç: 'c', ğ: 'g', ı: 'i', İ: 'i', ö: 'o', ş: 's', ü: 'u', Ç: 'c', Ğ: 'g', Ö: 'o', Ş: 's', Ü: 'u' };
  return s
    .split('')
    .map((c) => map[c] ?? c)
    .join('')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function formatDate(d: Date): string {
  return d.toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'Europe/Istanbul' });
}

export function isoDate(d: Date): string {
  return d.toISOString();
}
