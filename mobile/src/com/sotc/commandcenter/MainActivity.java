package com.sotc.commandcenter;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final String CLOUD_URL = "https://cloud-vm-monitor.vercel.app";
    private static final String LOCAL_DEFAULT_URL = "http://10.0.2.2:8765";
    private WebView webView;
    private ProgressBar progressBar;
    private TextView modeLabel;
    private String currentUrl = CLOUD_URL;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);

        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.setStatusBarColor(Color.parseColor("#080808"));
        window.setNavigationBarColor(Color.parseColor("#080808"));

        SharedPreferences prefs = getSharedPreferences("sotc_prefs", MODE_PRIVATE);
        currentUrl = prefs.getString("active_url", CLOUD_URL);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#080808"));

        // Barra Superior Dark Gothic Cinematic (#121216 com borda #8B0000 e Ouro Antigo #B59B61)
        LinearLayout topBar = new LinearLayout(this);
        topBar.setOrientation(LinearLayout.HORIZONTAL);
        topBar.setBackgroundColor(Color.parseColor("#121216"));
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        topBar.setPadding(24, 14, 24, 14);

        TextView brand = new TextView(this);
        brand.setText("\u2720 SOTC MOBILE");
        brand.setTextColor(Color.parseColor("#B59B61"));
        brand.setTextSize(14f);
        brand.setTypeface(Typeface.SERIF, Typeface.BOLD);
        LinearLayout.LayoutParams brandParams = new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f);
        brand.setLayoutParams(brandParams);

        modeLabel = new TextView(this);
        modeLabel.setText(currentUrl.contains("vercel.app") ? "CLOUD MIRROR" : "LAN COCKPIT");
        modeLabel.setTextColor(Color.parseColor("#73DB9C"));
        modeLabel.setTextSize(11f);
        modeLabel.setPadding(0, 0, 18, 0);

        Button btnCloud = createGothicButton("Nuvem");
        btnCloud.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                switchEndpoint(CLOUD_URL, "CLOUD MIRROR (Vercel + Neon)");
            }
        });

        Button btnReload = createGothicButton("\u21BB");
        btnReload.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (webView != null) {
                    webView.reload();
                    Toast.makeText(MainActivity.this, "Atualizando telemetria SOTC...", Toast.LENGTH_SHORT).show();
                }
            }
        });

        topBar.addView(brand);
        topBar.addView(modeLabel);
        topBar.addView(btnCloud);
        topBar.addView(btnReload);

        // Linha divisória Vermelho Sangue (#8B0000)
        View borderLine = new View(this);
        borderLine.setBackgroundColor(Color.parseColor("#8B0000"));
        borderLine.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 3));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setLayoutParams(new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 6));
        progressBar.setMax(100);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#080808"));
        LinearLayout.LayoutParams webParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1.0f);
        webView.setLayoutParams(webParams);

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setBuiltInZoomControls(true);
        ws.setDisplayZoomControls(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        ws.setUserAgentString(ws.getUserAgentString() + " SingOfTheCrossAndroid/1.0");

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
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() != null ? uri.getScheme().toLowerCase() : "";
                if ("http".equals(scheme) || "https".equals(scheme)) {
                    return false;
                }
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, uri);
                    startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Link exclusivo de Desktop: " + uri.toString(), Toast.LENGTH_SHORT).show();
                }
                return true;
            }
        });

        root.addView(topBar);
        root.addView(borderLine);
        root.addView(progressBar);
        root.addView(webView);
        setContentView(root);

        webView.loadUrl(currentUrl);
    }

    private Button createGothicButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(Color.parseColor("#E8E4DB"));
        b.setBackgroundColor(Color.parseColor("#281215"));
        b.setTextSize(11.5f);
        b.setPadding(20, 6, 20, 6);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.setMargins(10, 0, 0, 0);
        b.setLayoutParams(lp);
        return b;
    }

    private void switchEndpoint(String url, String label) {
        currentUrl = url;
        getSharedPreferences("sotc_prefs", MODE_PRIVATE).edit().putString("active_url", url).apply();
        modeLabel.setText(url.contains("vercel.app") ? "CLOUD MIRROR" : "LAN COCKPIT");
        webView.loadUrl(url);
        Toast.makeText(this, "Conectado a: " + label, Toast.LENGTH_SHORT).show();
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
