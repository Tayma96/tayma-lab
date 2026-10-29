// Precomputes the US map and the 9,000 "store" dots for the Blockbuster pilot.
// Dot placement is ILLUSTRATIVE (weighted by 2000 state population and big metros),
// not real store addresses. The video says so on screen.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { geoAlbersUsa, geoPath, geoContains } from "d3-geo";
import { feature, mesh } from "topojson-client";

const W = 1920, H = 1080;
const topo = JSON.parse(readFileSync(new URL("../node_modules/us-atlas/states-10m.json", import.meta.url)));
const states = feature(topo, topo.objects.states);
const lower48 = { type: "FeatureCollection", features: states.features.filter((f) => !["02", "15", "72", "60", "66", "69", "78"].includes(f.id)) };

const projection = geoAlbersUsa().fitExtent([[150, 120], [W - 150, H - 110]], lower48);
const path = geoPath(projection);

// 2000 census population, thousands, by state FIPS.
const POP = {"01":4447,"04":5131,"05":2673,"06":33872,"08":4301,"09":3406,"10":784,"11":572,"12":15982,"13":8186,"16":1294,"17":12419,"18":6080,"19":2926,"20":2688,"21":4042,"22":4469,"23":1275,"24":5296,"25":6349,"26":9938,"27":4919,"28":2845,"29":5595,"30":902,"31":1711,"32":1998,"33":1236,"34":8414,"35":1819,"36":18976,"37":8049,"38":642,"39":11353,"40":3451,"41":3421,"42":12281,"44":1048,"45":4012,"46":755,"47":5689,"48":20852,"49":2233,"50":609,"51":7079,"53":5894,"54":1808,"55":5364,"56":494};
// Big metros [lon, lat, weight]: stores clustered in cities.
const METROS = [[-74.0,40.7,19],[-118.2,34.05,13],[-87.6,41.9,9],[-95.4,29.8,5],[-96.8,32.8,5],[-75.2,39.95,6],[-77.0,38.9,5],[-80.2,25.8,5],[-84.4,33.75,4],[-71.06,42.36,4.5],[-122.4,37.77,7],[-112.07,33.45,3.5],[-122.33,47.6,3.5],[-83.05,42.33,4.5],[-93.27,44.98,3],[-117.16,32.72,3],[-104.99,39.74,2.5],[-90.2,38.63,2.5],[-76.6,39.29,2.5],[-82.46,27.95,2.5],[-80.0,40.44,2.4],[-122.68,45.52,2],[-81.69,41.5,2.2],[-121.5,38.58,1.8],[-94.58,39.1,1.8],[-115.14,36.17,1.5],[-86.16,39.77,1.6],[-97.74,30.27,1.4],[-98.49,29.42,1.6],[-81.38,28.54,1.6],[-80.84,35.23,1.5],[-86.78,36.16,1.3],[-90.05,35.15,1.2],[-90.07,29.95,1.3],[-111.89,40.76,1.3]];

let seed = 20001;
const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
const gauss = () => Math.sqrt(-2 * Math.log(rand() + 1e-12)) * Math.cos(2 * Math.PI * rand());

const byId = Object.fromEntries(lower48.features.map((f) => [f.id, f]));
const inUS = (lonlat) => lower48.features.some((f) => geoContains(f, lonlat));
const pick = (pairs) => { let r = rand() * pairs.reduce((s, [, w]) => s + w, 0); for (const [v, w] of pairs) if ((r -= w) <= 0) return v; return pairs[0][0]; };

const N = 9000, dots = [];
const statePairs = Object.entries(POP).filter(([id]) => byId[id]).map(([id, w]) => [id, w]);
while (dots.length < N) {
  let lonlat;
  if (rand() < 0.55) {
    const [lon, lat] = pick(METROS.map((m) => [m, m[2]]));
    lonlat = [lon + gauss() * 0.55, lat + gauss() * 0.4];
    if (!inUS(lonlat)) continue;
  } else {
    const f = byId[pick(statePairs)];
    const [[x0, y0], [x1, y1]] = (() => { const b = geoPath().bounds(f); return b; })();
    lonlat = [x0 + rand() * (x1 - x0), y0 + rand() * (y1 - y0)];
    if (!geoContains(f, lonlat)) continue;
  }
  const p = projection(lonlat);
  if (!p) continue;
  dots.push([Math.round(p[0] * 10) / 10, Math.round(p[1] * 10) / 10, Math.round(rand() * 1000) / 1000]);
}

const point = (lon, lat) => projection([lon, lat]).map((v) => Math.round(v * 10) / 10);
const out = {
  width: W, height: H,
  states: path(lower48),
  borders: path(mesh(topo, topo.objects.states, (a, b) => a !== b && byId[a.id] && byId[b.id])),
  oregon: path(byId["41"]),
  dots, // [x, y, order 0..1] - order decides when each dot is born and when it dies
  places: { losGatos: point(-121.96, 37.23), dallas: point(-96.8, 32.78), bend: point(-121.31, 44.06) },
};
mkdirSync(new URL("../src/data/", import.meta.url), { recursive: true });
writeFileSync(new URL("../src/data/harita.json", import.meta.url), JSON.stringify(out));
console.log(`dots=${dots.length} states=${(out.states.length / 1024).toFixed(0)}KB`, out.places);
