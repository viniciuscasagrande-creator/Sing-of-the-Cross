import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'br.com.sotc.monitor',
  appName: 'Sing Of The Cross',
  webDir: 'frontend',
  server: {
    url: 'https://cloud-vm-monitor.vercel.app',
    cleartext: true,
    androidScheme: 'https'
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1800,
      backgroundColor: '#080808',
      androidScaleType: 'CENTER_CROP',
      showSpinner: true,
      spinnerColor: '#B59B61'
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert']
    }
  }
};

export default config;
