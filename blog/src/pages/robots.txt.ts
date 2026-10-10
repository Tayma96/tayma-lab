import { absUrl } from '../lib/site';

export function GET() {
  // Not: GitHub Pages proje sitesinde robots.txt kök alan adında (tayma96.github.io/robots.txt) değil,
  // /tayma-lab/robots.txt altında yayınlanır. Arama motorları kökteki dosyayı okur; site haritasını
  // ayrıca Google Search Console'a gönderin. Özel alan adı bağlanırsa bu dosya kökte geçerli olur.
  const body = `User-agent: *\nAllow: /\n\nSitemap: ${absUrl('sitemap.xml')}\n`;
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}
