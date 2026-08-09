import Svg, { Path } from "react-native-svg";

import { theme } from "../constants/theme";

// The STRATUS horizon mark. V3.1.4.2 (brand correction pass): the previous
// version was a full semicircle with a small dot resting above it --
// explicitly wrong per the owner's reference, which shows the *small* mark
// used above "POWERED BY LGI": extremely restrained, thin, shallow, wide, no
// dot -- "primarily a simple orange horizon/arc," not a sunrise/gauge/
// sunburst. This is an elliptical arc (wide radius, shallow radius), not a
// circular one, which is what keeps it flat/horizon-like instead of a
// bulging semicircle. Used consistently anywhere the mark appears -- never
// reinterpreted per-screen.
//
// Sprint 3.6 (real-device correction pass, second reference sheet): the
// dedicated "BRAND ELEMENTS" swatch on the new reference sheet confirms this
// single-arc-no-dot reading (it's shown the same way -- just the arc, above
// "POWERED BY LGI" -- in that swatch and in every screen mockup's footer) --
// this was a genuine correction to keep, not something to walk back.
// Flattened further (0.22 -> 0.18 height ratio) and stroke bumped slightly
// (1.4 -> 1.6) to read as more precise/present without becoming a heavier
// shape, matching the swatch's razor-thin line weight more closely.
export function HorizonMark({
  size = 40,
  color = theme.accent,
  strokeWidth = 1.6,
}: {
  size?: number;
  color?: string;
  strokeWidth?: number;
}) {
  const height = size * 0.18;
  const halfW = size / 2 - strokeWidth;
  const archRy = height * 0.82;
  const cy = height * 0.86;

  return (
    <Svg width={size} height={height}>
      <Path
        d={`M ${size / 2 - halfW} ${cy} A ${halfW} ${archRy} 0 0 1 ${size / 2 + halfW} ${cy}`}
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        fill="none"
      />
    </Svg>
  );
}
