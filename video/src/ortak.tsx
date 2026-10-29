// Shared finishing layers: film grain and vignette. These are what stop flat
// vector graphics from looking like a slide deck.
import React from "react";
import { AbsoluteFill, Img, random, staticFile, useCurrentFrame } from "remotion";

export const Gren: React.FC<{ opacity?: number }> = ({ opacity = 0.07 }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ overflow: "hidden", mixBlendMode: "overlay", opacity, pointerEvents: "none" }}>
      <Img
        src={staticFile("grain.png")}
        style={{
          position: "absolute",
          width: 2048,
          height: 2048,
          imageRendering: "pixelated",
          translate: `${-2 * Math.round(random(`gx${frame}`) * 60)}px ${-2 * Math.round(random(`gy${frame}`) * 400)}px`,
        }}
      />
    </AbsoluteFill>
  );
};

export const Vinyet: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.55) 100%)",
    }}
  />
);
