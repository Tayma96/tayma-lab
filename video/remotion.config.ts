import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// Cloud container: use the pre-installed headless shell instead of downloading one.
// On your own computer, delete this line and Remotion downloads its own browser.
if (process.env.REMOTION_BROWSER) Config.setBrowserExecutable(process.env.REMOTION_BROWSER);
