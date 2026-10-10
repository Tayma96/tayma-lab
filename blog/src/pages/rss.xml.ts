import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { cfg, url } from '../lib/site';
import { getPublishedPosts } from '../lib/posts';

export async function GET(context: APIContext) {
  const posts = await getPublishedPosts();
  return rss({
    title: cfg.siteName,
    description: cfg.tagline,
    site: new URL(url(), context.site!).toString(),
    items: posts.map((p) => ({
      title: p.data.title,
      description: p.data.description,
      pubDate: p.data.date,
      link: url(`yazilar/${p.id}/`),
      categories: [p.data.category, ...p.data.tags],
    })),
    customData: '<language>tr-TR</language>',
  });
}
