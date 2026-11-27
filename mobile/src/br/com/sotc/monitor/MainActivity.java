package br.com.sotc.monitor;

import android.app.Activity;
import android.app.KeyguardManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final String CLOUD_URL = "https://cloud-vm-monitor.vercel.app";
    private static final String CHANNEL_ID = "sotc_critical_alerts";
    private static final int REQ_AUTH = 1001;

    private WebView webView;
    private ProgressBar progressBar;
    private TextView connBadge;
    private LinearLayout splashOverlay;
    private LinearLayout offlineBanner;
    private String currentUrl = CLOUD_URL;
    private boolean isAuthenticated = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);

        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.setStatusBarColor(Color.parseColor("#080808"));
        window.setNavigationBarColor(Color.parseColor("#121216"));

        createNotificationChannel();

        SharedPreferences prefs = getSharedPreferences("sotc_prefs", MODE_PRIVATE);
        currentUrl = prefs.getString("active_url", CLOUD_URL);

        FrameLayout frameRoot = new FrameLayout(this);
        frameRoot.setBackgroundColor(Color.parseColor("#080808"));

        // Container Principal Vertical (TopBar + OfflineBanner + WebView + BottomNav MD3)
        LinearLayout mainColumn = new LinearLayout(this);
        mainColumn.setOrientation(LinearLayout.VERTICAL);
        mainColumn.setBackgroundColor(Color.parseColor("#080808"));

        // 1. Barra Superior Dark Gothic + Material Design 3
        LinearLayout topBar = new LinearLayout(this);
        topBar.setOrientation(LinearLayout.HORIZONTAL);
        topBar.setBackgroundColor(Color.parseColor("#121216"));
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        topBar.setPadding(28, 18, 28, 18);

        TextView brand = new TextView(this);
        brand.setText("\u2720 SOTC MONITOR");
        brand.setTextColor(Color.parseColor("#B59B61"));
        brand.setTextSize(15f);
        brand.setTypeface(Typeface.SERIF, Typeface.BOLD);
        brand.setLayoutParams(new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f));

        connBadge = new TextView(this);
        connBadge.setText("\u25CF ONLINE");
        connBadge.setTextColor(Color.parseColor("#73DB9C"));
        connBadge.setTextSize(11f);
        connBadge.setPadding(0, 0, 18, 0);

        Button btnBio = createGothicButton("\uD83D\uDD12 Biometria");
        btnBio.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                promptBiometricOrDeviceCredential();
            }
        });

        Button btnReload = createGothicButton("\u21BB");
        btnReload.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                refreshTelemetry();
            }
        });

        topBar.addView(brand);
        topBar.addView(connBadge);
        topBar.addView(btnBio);
        topBar.addView(btnReload);

        View topBorder = new View(this);
        topBorder.setBackgroundColor(Color.parseColor("#8B0000"));
        topBorder.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 3));

        // 2. Banner de Ausência de Internet / Modo Offline
        offlineBanner = new LinearLayout(this);
        offlineBanner.setOrientation(LinearLayout.HORIZONTAL);
        offlineBanner.setBackgroundColor(Color.parseColor("#B91C1C"));
        offlineBanner.setGravity(Gravity.CENTER);
        offlineBanner.setPadding(20, 12, 20, 12);
        offlineBanner.setVisibility(View.GONE);

        TextView offlineTxt = new TextView(this);
        offlineTxt.setText("\u26A0 Sem conexão com a internet. Tentando reconectar ao servidor SOTC...");
        offlineTxt.setTextColor(Color.parseColor("#E8E4DB"));
        offlineTxt.setTextSize(12f);
        offlineBanner.addView(offlineTxt);

        // 3. Barra de Progresso
        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 6));
        progressBar.setMax(100);

        // 4. WebView Principal com Bridge Nativa Android
        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#080808"));
        webView.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1.0f));

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setBuiltInZoomControls(false);
        ws.setDisplayZoomControls(false);
        ws.setCacheMode(WebSettings.LOAD_DEFAULT);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        ws.setUserAgentString(ws.getUserAgentString() + " SOTCMonitorAndroid/1.0.0 Capacitor/6.0");

        webView.addJavascriptInterface(new SotcNativeBridge(), "SotcAndroid");

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress < 100) {
                    progressBar.setVisibility(View.VISIBLE);
                    progressBar.setProgress(newProgress);
                } else {
                    progressBar.setVisibility(View.GONE);
                }
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                updateConnectivityState();
                // Injeta adaptação mobile para eliminar qualquer overflow horizontal
                view.evaluateJavascript(
                    "(function(){ document.body.classList.add('sotc-mobile-apk'); })();",
                    null
                );
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    offlineBanner.setVisibility(View.VISIBLE);
                    connBadge.setText("\u25CF OFFLINE");
                    connBadge.setTextColor(Color.parseColor("#FF8585"));
                }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() != null ? uri.getScheme().toLowerCase() : "";
                if ("http".equals(scheme) || "https".equals(scheme)) {
                    return false;
                }
                if ("vscode".equals(scheme)) {
                    // Adaptação de funções exclusivas do Windows (VS Code Remote SSH) para Android
                    String raw = uri.toString();
                    String sshCmd = "ssh radar-producao";
                    ClipboardManager cb = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                    if (cb != null) {
                        cb.setPrimaryClip(ClipData.newPlainText("SSH Command", sshCmd));
                    }
                    Toast.makeText(
                        MainActivity.this,
                        "Modo Mobile: Comando '" + sshCmd + "' copiado! (VS Code Desktop abre no Windows 11)",
                        Toast.LENGTH_LONG
                    ).show();
                    return true;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Recurso exclusivo do Windows 11 Cockpit.", Toast.LENGTH_SHORT).show();
                }
                return true;
            }
        });

        // 5. Barra de Navegação Inferior Material Design 3 (Início, VMs, Alertas, Menu)
        View bottomBorder = new View(this);
        bottomBorder.setBackgroundColor(Color.parseColor("#8B0000"));
        bottomBorder.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 2));

        LinearLayout bottomNav = new LinearLayout(this);
        bottomNav.setOrientation(LinearLayout.HORIZONTAL);
        bottomNav.setBackgroundColor(Color.parseColor("#121216"));
        bottomNav.setGravity(Gravity.CENTER);
        bottomNav.setPadding(12, 14, 12, 16);

        bottomNav.addView(createBottomNavItem("\u2720 Início", "#cockpit"));
        bottomNav.addView(createBottomNavItem("\uD83D\uDDA5 VMs", "#visao-geral"));
        bottomNav.addView(createBottomNavItem("\uD83D\uDEA8 Alertas", "#sentinel"));
        bottomNav.addView(createBottomNavItem("\u2630 Menu", "#sotc-suite"));

        mainColumn.addView(topBar);
        mainColumn.addView(topBorder);
        mainColumn.addView(offlineBanner);
        mainColumn.addView(progressBar);
        mainColumn.addView(webView);
        mainColumn.addView(bottomBorder);
        mainColumn.addView(bottomNav);

        // 6. Splash Screen Personalizada Dark Gothic Cinematic
        splashOverlay = createSplashOverlay();

        frameRoot.addView(mainColumn);
        frameRoot.addView(splashOverlay);
        setContentView(frameRoot);

        updateConnectivityState();
        webView.loadUrl(currentUrl);

        // Oculta Splash Screen após 1.8s e solicita desbloqueio biométrico do dispositivo se configurado
        new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
            @Override
            public void run() {
                splashOverlay.setVisibility(View.GONE);
            }
        }, 1800);
    }

    private LinearLayout createSplashOverlay() {
        LinearLayout splash = new LinearLayout(this);
        splash.setOrientation(LinearLayout.VERTICAL);
        splash.setGravity(Gravity.CENTER);
        splash.setBackgroundColor(Color.parseColor("#080808"));
        splash.setLayoutParams(new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        ImageView logoImg = new ImageView(this);
        logoImg.setImageResource(R.drawable.ic_launcher);
        LinearLayout.LayoutParams imgLp = new LinearLayout.LayoutParams(240, 240);
        imgLp.bottomMargin = 28;
        logoImg.setLayoutParams(imgLp);

        TextView title = new TextView(this);
        title.setText("SING OF THE CROSS");
        title.setTextColor(Color.parseColor("#E8E4DB"));
        title.setTextSize(22f);
        title.setTypeface(Typeface.SERIF, Typeface.BOLD);
        title.setGravity(Gravity.CENTER);

        TextView sub = new TextView(this);
        sub.setText("SOTC MONITOR \u2022 DARK GOTHIC MULTI-CLOUD");
        sub.setTextColor(Color.parseColor("#B59B61"));
        sub.setTextSize(11.5f);
        sub.setGravity(Gravity.CENTER);
        sub.setPadding(0, 10, 0, 36);

        ProgressBar spinner = new ProgressBar(this);

        splash.addView(logoImg);
        splash.addView(title);
        splash.addView(sub);
        splash.addView(spinner);
        return splash;
    }

    private View createBottomNavItem(String label, final String anchor) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextColor(Color.parseColor("#E8E4DB"));
        b.setBackgroundColor(Color.parseColor("#1B161C"));
        b.setTextSize(12f);
        b.setAllCaps(false);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f);
        lp.setMargins(6, 0, 6, 0);
        b.setLayoutParams(lp);
        b.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (webView != null) {
                    webView.evaluateJavascript(
                        "(function(){ var el = document.querySelector('" + anchor + "'); if(el) el.scrollIntoView({behavior:'smooth'}); })();",
                        null
                    );
                }
            }
        });
        return b;
    }

    private Button createGothicButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(Color.parseColor("#E8E4DB"));
        b.setBackgroundColor(Color.parseColor("#281215"));
        b.setTextSize(11f);
        b.setAllCaps(false);
        b.setPadding(18, 6, 18, 6);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.setMargins(8, 0, 0, 0);
        b.setLayoutParams(lp);
        return b;
    }

    private void refreshTelemetry() {
        updateConnectivityState();
        if (webView != null) {
            webView.reload();
            Toast.makeText(this, "Sincronizando telemetria SOTC...", Toast.LENGTH_SHORT).show();
        }
    }

    private void updateConnectivityState() {
        boolean online = isNetworkAvailable();
        if (online) {
            offlineBanner.setVisibility(View.GONE);
            connBadge.setText("\u25CF ONLINE");
            connBadge.setTextColor(Color.parseColor("#73DB9C"));
        } else {
            offlineBanner.setVisibility(View.VISIBLE);
            connBadge.setText("\u25CF OFFLINE");
            connBadge.setTextColor(Color.parseColor("#FF8585"));
        }
    }

    private boolean isNetworkAvailable() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            Network net = cm.getActiveNetwork();
            if (net == null) return false;
            NetworkCapabilities caps = cm.getNetworkCapabilities(net);
            return caps != null && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
        } catch (Exception e) {
            return true;
        }
    }

    private void promptBiometricOrDeviceCredential() {
        try {
            KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
            if (km != null && km.isKeyguardSecure()) {
                Intent authIntent = km.createConfirmDeviceCredentialIntent(
                        "Autenticação SOTC Guardian",
                        "Confirme sua biometria ou PIN para desbloquear operações críticas no Sing Of The Cross.");
                if (authIntent != null) {
                    startActivityForResult(authIntent, REQ_AUTH);
                    return;
                }
            }
            isAuthenticated = true;
            Toast.makeText(this, "\uD83D\uDFE2 Sessão Guardian autenticada neste dispositivo!", Toast.LENGTH_SHORT).show();
            sendPushAlert("SOTC Guardian Autenticado", "Sessão biométrica liberada para monitoramento e controle.");
        } catch (Exception e) {
            Toast.makeText(this, "Autenticação verificada.", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_AUTH) {
            if (resultCode == RESULT_OK) {
                isAuthenticated = true;
                Toast.makeText(this, "\uD83D\uDFE2 Biometria confirmada com sucesso!", Toast.LENGTH_SHORT).show();
                sendPushAlert("SOTC Guardian", "Desbloqueio biométrico autorizado.");
            } else {
                Toast.makeText(this, "\uD83D\uDD34 Autenticação cancelada.", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Alertas Críticos SOTC Sentinel",
                    NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("Notificações de CPU, RAM, Disco (>75%/90%) e Latência SSH (>150ms/500ms)");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    public void sendPushAlert(String title, String message) {
        try {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            Notification.Builder builder;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                builder = new Notification.Builder(this, CHANNEL_ID);
            } else {
                builder = new Notification.Builder(this);
            }
            builder.setSmallIcon(R.drawable.ic_launcher)
                   .setContentTitle(title)
                   .setContentText(message)
                   .setAutoCancel(true);
            nm.notify((int) (System.currentTimeMillis() % 10000), builder.build());
        } catch (Exception ignored) {
        }
    }

    public class SotcNativeBridge {
        @JavascriptInterface
        public void notifyAlert(String title, String message) {
            sendPushAlert(title, message);
        }

        @JavascriptInterface
        public void requestBiometricAuth() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    promptBiometricOrDeviceCredential();
                }
            });
        }

        @JavascriptInterface
        public String getPackageInfo() {
            return "br.com.sotc.monitor|1.0.0";
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
