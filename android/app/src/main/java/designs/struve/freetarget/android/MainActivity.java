package designs.struve.freetarget.android;

import android.app.Activity;
import android.graphics.Color;
import android.content.pm.ActivityInfo;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.net.Uri;
import android.os.Bundle;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.Map;

public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String INDEX = "https://" + HOST + "/index.html";
    private static final Map<String, String> ASSETS = Map.of(
            "/index.html", "text/html", "/android.js", "application/javascript",
            "/mobile.css", "text/css", "/android.css", "text/css");
    private WebView view;
    private TargetConnection target;
    private final BroadcastReceiver usbPermission = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (TargetConnection.USB_PERMISSION.equals(intent.getAction())) {
                target.usbPermissionResult(intent.getLongExtra("attempt", -1));
            }
        }
    };

    private boolean isTabletLayout() {
        return getResources().getConfiguration().smallestScreenWidthDp >= 600;
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (!isTabletLayout()) {
            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        target = new TargetConnection(this);
        IntentFilter usbFilter = new IntentFilter(TargetConnection.USB_PERMISSION);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(usbPermission, usbFilter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(usbPermission, usbFilter);
        }
        view = new WebView(this);
        WebSettings settings = view.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        view.setWebChromeClient(new WebChromeClient());
        view.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView web, WebResourceRequest request) {
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView web, WebResourceRequest request) {
                Uri url = request.getUrl();
                String path = url.getPath();
                if ("https".equals(url.getScheme()) && HOST.equals(url.getHost()) && path != null
                        && ASSETS.containsKey(path)) {
                    try {
                        return new WebResourceResponse(ASSETS.get(path), "UTF-8",
                                getAssets().open(path.substring(1)));
                    } catch (IOException ignored) {
                        // Treat missing bundled assets like any other unavailable resource.
                    }
                }
                return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found",
                        Map.of(), new ByteArrayInputStream(new byte[0]));
            }
        });
        view.addJavascriptInterface(new TargetApi(), "FTAndroidTarget");
        setContentView(view);
        view.loadUrl(INDEX);
    }

    @Override protected void onStop() {
        if (view != null) view.evaluateJavascript("window.FTDesktopPrepareClose?.()", null);
        if (target != null) target.disconnect("Disconnected when the app left the foreground.");
        super.onStop();
    }

    @Override protected void onDestroy() {
        unregisterReceiver(usbPermission);
        if (view != null) {
            view.removeJavascriptInterface("FTAndroidTarget");
            view.destroy();
        }
        super.onDestroy();
    }

    final class TargetApi {
        @JavascriptInterface public void setNavigationAppearance(boolean dark, String sidebarColor) {
            int color = Color.WHITE;
            if (dark) {
                color = sidebarColor != null && sidebarColor.matches("#[0-9a-fA-F]{6}")
                        ? Color.parseColor(sidebarColor) : Color.rgb(20, 34, 53);
            }
            final int background = color;
            runOnUiThread(() -> {
                if (isDestroyed()) return;
                getWindow().setNavigationBarColor(background);
                WindowInsetsController controller = getWindow().getInsetsController();
                if (controller != null) {
                    int lightNav = WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
                    controller.setSystemBarsAppearance(dark ? 0 : lightNav, lightNav);
                }
            });
        }

        @JavascriptInterface public boolean isTablet() {
            return isTabletLayout();
        }

        @JavascriptInterface public String versionName() {
            return BuildConfig.VERSION_NAME;
        }

        @JavascriptInterface public String request(String method, String path, String payload) {
            try {
                Uri uri = Uri.parse(path);
                JSONObject data;
                if ("GET".equals(method) && "/api/events".equals(uri.getPath())) {
                    data = target.poll(Long.parseLong(uri.getQueryParameter("after")));
                } else if ("GET".equals(method) && "/api/serial-ports".equals(path)) {
                    data = target.serialPorts();
                } else if ("POST".equals(method) && "/api/connect".equals(path)) {
                    target.connect(new JSONObject(payload));
                    data = new JSONObject().put("ok", true);
                } else if ("POST".equals(method) && "/api/disconnect".equals(path)) {
                    target.disconnect("Disconnected");
                    data = new JSONObject().put("ok", true);
                } else if ("POST".equals(method) && "/api/clear-diagnostics".equals(path)) {
                    data = target.clear();
                } else {
                    return response(404, new JSONObject().put("error", "Unavailable in the Android beta."));
                }
                return response(200, data);
            } catch (IllegalArgumentException | JSONException error) {
                try {
                    return response(400, new JSONObject().put("error", error.getMessage()));
                } catch (JSONException ignored) {
                    return "{\"status\":400,\"body\":{}}";
                }
            }
        }

        private String response(int status, JSONObject data) throws JSONException {
            return new JSONObject().put("status", status).put("body", data).toString();
        }
    }
}
