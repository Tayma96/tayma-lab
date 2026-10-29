// Pilot: the first ~29 s of "The $50 Million Mistake" (Blockbuster & Netflix).
// Timings follow the narration in public/blockbuster-hook-mix.m4a (30 fps).
import React from "react";
import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame } from "remotion";
import harita from "./data/harita.json";
import { BASLIK, METIN, RENK } from "./stil";
import { Gren, Vinyet } from "./ortak";

const W = 1920;
const H = 1080;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const yavas = Easing.bezier(0.65, 0, 0.35, 1);
const cikis = Easing.bezier(0.16, 1, 0.3, 1);

type Nokta = [number, number, number];
const NOKTALAR = harita.dots as Nokta[];
const BEND = harita.places.bend as [number, number];
const LOS_GATOS = harita.places.losGatos as [number, number];
const DALLAS = harita.places.dallas as [number, number];
const KONTROL: [number, number] = [(LOS_GATOS[0] + DALLAS[0]) / 2, Math.min(LOS_GATOS[1], DALLAS[1]) - 190];

// Camera as an SVG viewBox, so zooming stays vector-sharp.
const KAMERA_KARE = [0, 120, 284, 330, 590, 690];
const KAMERA_KUTU: [number, number, number, number][] = [
  [120, 250, 1150, 646.9],
  [90, 230, 1240, 697.5],
  [90, 230, 1240, 697.5],
  [0, 0, 1920, 1080],
  [0, 0, 1920, 1080],
  [BEND[0] - 300, BEND[1] - 168.75, 600, 337.5],
];
const kamera = (frame: number) =>
  [0, 1, 2, 3].map((i) =>
    interpolate(frame, KAMERA_KARE, KAMERA_KUTU.map((k) => k[i]), { ...clamp, easing: yavas }),
  ) as [number, number, number, number];
const ekrana = ([x, y]: [number, number], [vx, vy, vw, vh]: number[]) => [((x - vx) / vw) * W, ((y - vy) / vh) * H];

// Stores are born 292-445 and die 478-600, in the precomputed random order.
const dogum = (f: number) => interpolate(f, [292, 445], [0, 1], { ...clamp, easing: cikis });
const olum = (f: number) => interpolate(f, [478, 556, 610], [0, 0.97, 1], { ...clamp, easing: Easing.in(Easing.quad) });

const egri = (t: number) => {
  const u = 1 - t;
  return [
    u * u * LOS_GATOS[0] + 2 * u * t * KONTROL[0] + t * t * DALLAS[0],
    u * u * LOS_GATOS[1] + 2 * u * t * KONTROL[1] + t * t * DALLAS[1],
  ];
};

// The dash is drawn by arc length; the moving dot must use the same parameter.
const ORNEK = Array.from({ length: 201 }, (_, i) => egri(i / 200));
const BIRIKIM = ORNEK.reduce<number[]>((acc, p, i) => {
  acc.push(i === 0 ? 0 : acc[i - 1] + Math.hypot(p[0] - ORNEK[i - 1][0], p[1] - ORNEK[i - 1][1]));
  return acc;
}, []);
const uzunluktanT = (oran: number) => {
  const hedef = oran * BIRIKIM[BIRIKIM.length - 1];
  const i = BIRIKIM.findIndex((v) => v >= hedef);
  return i <= 0 ? 0 : (i - 1 + (hedef - BIRIKIM[i - 1]) / (BIRIKIM[i] - BIRIKIM[i - 1] || 1)) / 200;
};

const Harita: React.FC = () => {
  const frame = useCurrentFrame();
  const vb = kamera(frame);
  const b = dogum(frame);
  const d = olum(frame);
  let canli = "";
  let sonmus = "";
  for (const [x, y, sira] of NOKTALAR) {
    if (sira >= b) continue;
    if (sira >= d) canli += `M${x} ${y}h0`;
    else sonmus += `M${x} ${y}h0`;
  }
  const rota = interpolate(frame, [14, 96], [0, 1], { ...clamp, easing: yavas });
  const [ux, uy] = egri(uzunluktanT(rota));
  const sonIsik = interpolate(frame, [560, 600], [0, 1], clamp);
  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(frame, [0, 18, 126, 142, 284, 312, 692, 730], [0, 1, 1, 0.16, 0.16, 1, 1, 0], clamp),
      }}
    >
      <svg viewBox={vb.join(" ")} width={W} height={H}>
        <defs>
          <radialGradient id="parilti">
            <stop offset="0%" stopColor={RENK.altinYumusak} stopOpacity={0.9} />
            <stop offset="100%" stopColor={RENK.altin} stopOpacity={0} />
          </radialGradient>
        </defs>
        <path d={harita.states} fill={RENK.kara} stroke={RENK.kontur} strokeWidth={1.4} vectorEffect="non-scaling-stroke" />
        <path d={harita.borders} fill="none" stroke={RENK.sinir} strokeWidth={0.9} vectorEffect="non-scaling-stroke" />
        <path
          d={harita.oregon}
          fill={RENK.altin}
          fillOpacity={interpolate(frame, [600, 660], [0, 0.07], clamp)}
          stroke={RENK.altin}
          strokeOpacity={interpolate(frame, [600, 660], [0, 0.5], clamp)}
          strokeWidth={1.4}
          vectorEffect="non-scaling-stroke"
        />
        {frame < 160 ? (
          <g opacity={interpolate(frame, [100, 140], [1, 0], clamp)}>
            <path
              d={`M${LOS_GATOS.join(" ")}Q${KONTROL.join(" ")} ${DALLAS.join(" ")}`}
              fill="none"
              stroke={RENK.altin}
              strokeWidth={(vb[2] / W) * 3}
              strokeDasharray={`${rota} 1`}
              pathLength={1}
            />
            <circle cx={ux} cy={uy} r={(vb[2] / W) * 7} fill={RENK.altinYumusak} opacity={rota < 1 ? 1 : 0} />
            <circle cx={LOS_GATOS[0]} cy={LOS_GATOS[1]} r={(vb[2] / W) * 6} fill={RENK.yazi} />
            <circle
              cx={DALLAS[0]}
              cy={DALLAS[1]}
              r={(vb[2] / W) * interpolate(frame, [92, 104], [0, 9], { ...clamp, easing: cikis })}
              fill={RENK.altin}
            />
          </g>
        ) : null}
        <path d={sonmus} stroke={RENK.sonuk} strokeWidth={3} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        <path d={canli} stroke={RENK.altin} strokeWidth={3.2} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        {b > 0.6 ? (
          <>
            <circle cx={BEND[0]} cy={BEND[1]} r={(vb[2] / W) * 46} fill="url(#parilti)" opacity={sonIsik} />
            <circle
              cx={BEND[0]}
              cy={BEND[1]}
              r={(vb[2] / W) * interpolate(frame, [560, 610], [1.6, 5.5], clamp)}
              fill={RENK.altinYumusak}
            />
          </>
        ) : null}
      </svg>
    </AbsoluteFill>
  );
};

const Etiket: React.FC<{ yer: [number, number]; baslik: string; alt?: string; acilis: number; kapanis: number; yon?: "sag" | "sol" }> = ({
  yer,
  baslik,
  alt,
  acilis,
  kapanis,
  yon = "sag",
}) => {
  const frame = useCurrentFrame();
  const [x, y] = ekrana(yer, kamera(frame));
  return (
    <div
      style={{
        position: "absolute",
        left: yon === "sag" ? x + 22 : undefined,
        right: yon === "sol" ? W - x + 22 : undefined,
        top: y - 22,
        fontFamily: METIN,
        color: RENK.yazi,
        textAlign: yon === "sag" ? "left" : "right",
        opacity: interpolate(frame, [acilis, acilis + 14, kapanis - 12, kapanis], [0, 1, 1, 0], clamp),
        translate: `0px ${interpolate(frame, [acilis, acilis + 14], [10, 0], { ...clamp, easing: cikis })}px`,
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: "0.18em" }}>{baslik}</div>
      {alt ? <div style={{ fontSize: 22, fontWeight: 400, color: RENK.yaziIkincil, marginTop: 4 }}>{alt}</div> : null}
    </div>
  );
};

const KoseBaslik: React.FC<{ ust: string; ana: string; renk?: string; acilis: number; kapanis: number }> = ({
  ust,
  ana,
  renk = RENK.yazi,
  acilis,
  kapanis,
}) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        position: "absolute",
        left: 110,
        top: 90,
        opacity: interpolate(frame, [acilis, acilis + 12, kapanis - 10, kapanis], [0, 1, 1, 0], clamp),
      }}
    >
      <div style={{ fontFamily: METIN, fontWeight: 600, fontSize: 22, letterSpacing: "0.3em", color: RENK.yaziIkincil }}>{ust}</div>
      <div style={{ fontFamily: BASLIK, fontWeight: 900, fontSize: 104, color: renk, lineHeight: 1.05, marginTop: 6 }}>{ana}</div>
    </div>
  );
};

const MagazaSayaci: React.FC = () => {
  const frame = useCurrentFrame();
  const sayi = frame < 476 ? Math.round(dogum(frame) * 9000) : Math.max(1, Math.round((1 - olum(frame)) * 9000));
  const iflas = frame >= 476;
  return (
    <div style={{ position: "absolute", left: 110, bottom: 80, opacity: interpolate(frame, [290, 304, 680, 700], [0, 1, 1, 0], clamp) }}>
      <div style={{ fontFamily: METIN, fontWeight: 600, fontSize: 22, letterSpacing: "0.3em", color: iflas ? RENK.kirmizi : RENK.yaziIkincil }}>
        {iflas ? "2010 · CHAPTER 11" : "BLOCKBUSTER STORES · 2004"}
      </div>
      <div style={{ fontFamily: BASLIK, fontWeight: 900, fontSize: 124, color: RENK.yazi, lineHeight: 1.05, marginTop: 6, fontVariantNumeric: "tabular-nums" }}>
        {sayi.toLocaleString("en-US")}
      </div>
    </div>
  );
};

const Fiyat: React.FC = () => {
  const frame = useCurrentFrame(); // relative to the Sequence
  const deger = interpolate(frame, [6, 50], [0, 50_000_000], { ...clamp, easing: cikis });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: interpolate(frame, [0, 8, 68, 78], [0, 1, 1, 0], clamp) }}>
      <div style={{ fontFamily: METIN, fontWeight: 600, fontSize: 26, letterSpacing: "0.32em", color: RENK.yaziIkincil }}>THE ASKING PRICE</div>
      <div
        style={{
          fontFamily: BASLIK,
          fontWeight: 900,
          fontSize: 190,
          color: RENK.altin,
          fontVariantNumeric: "tabular-nums",
          marginTop: 10,
          scale: interpolate(frame, [0, 78], [1, 1.04], clamp),
        }}
      >
        ${Math.round(deger).toLocaleString("en-US")}
      </div>
      <div style={{ fontFamily: METIN, fontWeight: 500, fontSize: 26, color: RENK.yaziIkincil, marginTop: 6 }}>for all of Netflix · 2000</div>
    </AbsoluteFill>
  );
};

const Red: React.FC = () => {
  const frame = useCurrentFrame();
  const damga = interpolate(frame, [30, 38], [1.6, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
  const sarsinti = frame >= 38 && frame < 46 ? Math.sin(frame * 2.7) * (46 - frame) * 0.8 : 0;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: interpolate(frame, [0, 10, 70, 80], [0, 1, 1, 0], clamp) }}>
      <div style={{ fontFamily: METIN, fontWeight: 600, fontSize: 26, letterSpacing: "0.32em", color: RENK.yaziIkincil }}>BLOCKBUSTER'S ANSWER</div>
      <div
        style={{
          marginTop: 34,
          padding: "10px 46px",
          border: `8px solid ${RENK.kirmizi}`,
          borderRadius: 10,
          fontFamily: METIN,
          fontWeight: 700,
          fontSize: 132,
          letterSpacing: "0.08em",
          color: RENK.kirmizi,
          rotate: "-6deg",
          opacity: interpolate(frame, [30, 34], [0, 0.92], clamp),
          scale: damga,
          translate: `${sarsinti}px 0px`,
        }}
      >
        DECLINED
      </div>
      <div style={{ position: "absolute", bottom: 70, fontFamily: METIN, fontSize: 20, color: RENK.yaziIkincil, opacity: 0.8 }}>
        As told by Netflix co-founder Marc Randolph in "That Will Never Work" (2019)
      </div>
    </AbsoluteFill>
  );
};

const Soru: React.FC = () => {
  const frame = useCurrentFrame();
  const kelimeler = "How does a giant miss something this obvious?".split(" ");
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: interpolate(frame, [78, 92], [1, 0], clamp) }}>
      <div style={{ fontFamily: BASLIK, fontWeight: 700, fontSize: 84, color: RENK.yazi, maxWidth: 1300, textAlign: "center", lineHeight: 1.2 }}>
        {kelimeler.map((k, i) => (
          <span
            key={i}
            style={{
              opacity: interpolate(frame, [4 + i * 9, 16 + i * 9], [0, 1], clamp),
              color: k.startsWith("obvious") ? RENK.altin : undefined,
            }}
          >
            {k}{" "}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const Kapanis: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: interpolate(frame, [6, 30, 80, 101], [0, 1, 1, 0], clamp) }}>
      <div style={{ fontFamily: METIN, fontWeight: 600, fontSize: 24, letterSpacing: "0.42em", color: RENK.yaziIkincil }}>THE BLOCKBUSTER STORY</div>
      <div
        style={{
          height: 3,
          background: RENK.altin,
          margin: "28px 0",
          width: interpolate(frame, [10, 50], [0, 760], { ...clamp, easing: cikis }),
        }}
      />
      <div
        style={{
          fontFamily: BASLIK,
          fontWeight: 900,
          fontSize: 132,
          color: RENK.yazi,
          letterSpacing: "0.01em",
          scale: interpolate(frame, [6, 101], [0.97, 1.02], clamp),
        }}
      >
        The $50 Million Mistake
      </div>
    </AbsoluteFill>
  );
};

export const BlockbusterHook: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: RENK.zemin }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 40%, #16202c 0%, rgba(10,14,19,0) 70%)" }} />
      <Harita />
      <Etiket yer={LOS_GATOS} baslik="LOS GATOS, CA" alt="Netflix HQ" acilis={8} kapanis={126} yon="sol" />
      <Etiket yer={DALLAS} baslik="DALLAS, TX" alt="Blockbuster HQ" acilis={92} kapanis={130} />
      <KoseBaslik ust="DALLAS · 2000" ana="The Meeting" acilis={4} kapanis={124} />
      <Sequence from={126} durationInFrames={78}>
        <Fiyat />
      </Sequence>
      <Sequence from={204} durationInFrames={80}>
        <Red />
      </Sequence>
      <MagazaSayaci />
      <Etiket yer={BEND} baslik="BEND, OREGON" alt="The last Blockbuster on Earth" acilis={630} kapanis={700} />
      <div style={{ position: "absolute", right: 110, bottom: 60, fontFamily: METIN, fontSize: 18, color: RENK.yaziIkincil, opacity: 0.7 }}>
        <Sequence from={300} durationInFrames={300} layout="none">
          Dots: illustrative placement, not exact store locations
        </Sequence>
      </div>
      <Sequence from={692} durationInFrames={92}>
        <Soru />
      </Sequence>
      <Sequence from={784} durationInFrames={101}>
        <Kapanis />
      </Sequence>
      <Vinyet />
      <Gren />
    </AbsoluteFill>
  );
};
