// Channel look: one place for colours and fonts, so every video shares the same style.
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

export const RENK = {
  zemin: "#0a0e13",
  kara: "#121922",
  sinir: "#243244",
  kontur: "#3a4d66",
  altin: "#f2b33d",
  altinYumusak: "#f7d28a",
  sonuk: "#2a3340",
  yazi: "#eef1f5",
  yaziIkincil: "#9aa7b8",
  kirmizi: "#d9463b",
};

export const BASLIK = "Playfair Display";
export const METIN = "Inter";

const fontlar: [string, string, string][] = [
  [BASLIK, "700", "fonts/playfair-display-latin-700-normal.woff2"],
  [BASLIK, "900", "fonts/playfair-display-latin-900-normal.woff2"],
  [METIN, "400", "fonts/inter-latin-400-normal.woff2"],
  [METIN, "500", "fonts/inter-latin-500-normal.woff2"],
  [METIN, "600", "fonts/inter-latin-600-normal.woff2"],
  [METIN, "700", "fonts/inter-latin-700-normal.woff2"],
];
for (const [family, weight, file] of fontlar) {
  loadFont({ family, url: staticFile(file), weight });
}
