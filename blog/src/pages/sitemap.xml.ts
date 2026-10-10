import { absUrl, slugify } from '../lib/site';
import { getPublishedPosts } from '../lib/posts';

export async function GET() {
  const posts = await getPublishedPosts();
  const latest = posts[0]?.data.date ?? new Date();
  const entries: { loc: string; lastmod: Date }[] = [
    { loc: absUrl(), lastmod: latest },
    { loc: absUrl('kategori/'), lastmod: latest },
    ...[...new Set(posts.map((p) => p.data.category))].map((c) => ({ loc: absUrl(`kategori/${slugify(c)}/`), lastmod: latest })),
    ...posts.map((p) => ({ loc: absUrl(`yazilar/${p.id}/`), lastmod: p.data.updated ?? p.data.date })),
    { loc: absUrl('hakkinda/'), lastmod: latest },
    { loc: absUrl('ortaklik-aciklamasi/'), lastmod: latest },
    { loc: absUrl('gizlilik-ve-cerezler/'), lastmod: latest },
  ];
  const body =
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    entries.map((e) => `  <url><loc>${e.loc}</loc><lastmod>${e.lastmod.toISOString().slice(0, 10)}</lastmod></url>`).join('\n') +
    '\n</urlset>\n';
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
