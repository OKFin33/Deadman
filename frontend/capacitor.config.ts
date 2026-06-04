import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.okfin.deadman",
  appName: "要是我来",
  webDir: "dist",
  android: {
    allowMixedContent: true,
  },
  server: {
    androidScheme: "https",
    cleartext: true,
  },
  plugins: {
    CapacitorHttp: {
      enabled: true,
    },
  },
};

export default config;
