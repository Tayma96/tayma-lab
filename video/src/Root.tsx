import React from "react";
import { Composition } from "remotion";
import "./stil";
import { BlockbusterHook } from "./BlockbusterHook";

export const RemotionRoot: React.FC = () => (
  <Composition id="BlockbusterHook" component={BlockbusterHook} durationInFrames={885} fps={30} width={1920} height={1080} />
);
