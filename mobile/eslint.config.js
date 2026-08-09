// V3.1.4 BATCH-2: first ESLint config for this project. Uses Expo's flat
// config (eslint-config-expo), which already bundles React/React Native/
// TypeScript/React Hooks rules appropriate for this stack.
const expoConfig = require("eslint-config-expo/flat");

module.exports = [
  ...expoConfig,
  {
    ignores: ["dist/*", "node_modules/*", ".expo/*"],
  },
  {
    // eslint-config-expo pulls in eslint-plugin-react-hooks@7, whose
    // react-hooks/refs, react-hooks/purity, react-hooks/set, and react/use
    // rules assume React Compiler-style components (no ref access, no
    // Math.random(), during render). This app's classic Animated API usage
    // (useRef(new Animated.Value(...)) then .interpolate() during render --
    // e.g. FadeIn.tsx, LoganCore.tsx) and one-time useMemo-seeded
    // Math.random() layout generation (AtmosphereField.tsx) are both
    // standard, correct React Native patterns that predate and aren't
    // compatible with those rules; they accounted for ~95 of the ~97
    // findings on first run (V3.1.4 BATCH-2). Rewriting the animation/
    // atmosphere architecture to be React-Compiler-pure is out of scope for
    // adding lint tooling -- disabled here rather than silenced per-line.
    // (Vessel.tsx/AttentionField.tsx moved off classic Animated onto
    // Reanimated in V3.1.4.1, a Sprint 3.5 device-validation fix -- they no
    // longer need this exception, but the rules stay off globally for the
    // files that still do.)
    rules: {
      "react-hooks/refs": "off",
      "react-hooks/purity": "off",
      "react-hooks/set": "off",
      "react/use": "off",
      // react-hooks/set-state-in-effect flags the standard fetch-on-mount
      // pattern (index.tsx/memory.tsx's useEffect(() => { load() }, [...]))
      // and AttentionField.tsx's derived-default-focus effect. BATCH-4/5
      // (V3.1.4) centralizes API request handling in these exact files;
      // revisit this rule then rather than partially refactoring now only
      // to redo it. Tracked, not silently dropped.
      "react-hooks/set-state-in-effect": "off",
    },
  },
];
