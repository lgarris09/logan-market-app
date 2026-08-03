import { View } from "react-native";

import { AtmosphereField } from "../components/atmosphere/AtmosphereField";

// Sprint 1 deliverable, viewed in isolation: the medium itself, before any
// entity, text, or interaction is layered on top of it. Reachable from the
// menu on the real home screen so it can be judged on its own without
// disturbing the working AttentionField experience.
export default function AtmospherePreviewScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: "#000" }}>
      <AtmosphereField />
    </View>
  );
}
