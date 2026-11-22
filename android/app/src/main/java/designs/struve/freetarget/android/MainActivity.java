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
import android.view.View;
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
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String INDEX = "https://" + HOST + "/index.html";
    private static final int REQUEST_SYNC_EXPORT = 501;
    private static final int REQUEST_SYNC_IMPORT = 502;
    private static final int MAX_SYNC_BYTES = 32 * 1024 * 1024;
    private static final Map<String, String> ASSETS = createAssetMap();

    private static Map<String, String> createAssetMap() {
        Map<String, String> assets = new HashMap<>();
        assets.put("/index.html", "text/html");
        assets.put("/android.js", "application/javascript");
        assets.put("/mobile.css", "text/css");
        assets.put("/android.css", "text/css");
        assets.put("/portable_sync_core.js", "application/javascript");
        return Collections.unmodifiableMap(assets);
    }

    private WebView view;
    private TargetConnection target;
    private String pendingSyncExport;
    private boolean syncPickerOpen;
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
                        if ("/index.html".equals(path)) {
                            try (InputStream input = getAssets().open("index.html")) {
                                String html = new String(readLimited(input, MAX_SYNC_BYTES), StandardCharsets.UTF_8);
                                html = html.replace("</head>", "<script src=\"https://" + HOST
                                        + "/portable_sync_core.js\"></script></head>");
                                return new WebResourceResponse(ASSETS.get(path), "UTF-8",
                                        new ByteArrayInputStream(html.getBytes(StandardCharsets.UTF_8)));
                            }
                        }
                        return new WebResourceResponse(ASSETS.get(path), "UTF-8",
                                getAssets().open(path.substring(1)));
                    } catch (IOException ignored) {
                        // Treat missing bundled assets like any other unavailable resource.
                    }
                }
                return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found",
                        Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
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

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_SYNC_EXPORT && requestCode != REQUEST_SYNC_IMPORT) return;
        syncPickerOpen = false;
        if (resultCode != RESULT_OK || data == null || data.getData() == null) {
            if (requestCode == REQUEST_SYNC_EXPORT) reportSyncExport(false, "Sync export canceled.");
            else reportSyncImport(null, "Sync import canceled.");
            return;
        }
        Uri uri = data.getData();
        if (requestCode == REQUEST_SYNC_EXPORT) {
            String json = pendingSyncExport;
            pendingSyncExport = null;
            if (json == null) {
                reportSyncExport(false, "The sync export expired. Try again.");
                return;
            }
            try (OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
                if (output == null) throw new IOException("Could not open the selected file.");
                output.write(json.getBytes(StandardCharsets.UTF_8));
                output.flush();
                reportSyncExport(true, "Sync file saved.");
            } catch (IOException error) {
                reportSyncExport(false, "Could not save the sync file: " + error.getMessage());
            }
        } else {
            try (InputStream input = getContentResolver().openInputStream(uri)) {
                if (input == null) throw new IOException("Could not open the selected file.");
                String json = new String(readLimited(input, MAX_SYNC_BYTES), StandardCharsets.UTF_8);
                new JSONObject(json);
                reportSyncImport(json, null);
            } catch (IOException | JSONException error) {
                reportSyncImport(null, "Could not read the sync file: " + error.getMessage());
            }
        }
    }

    private void exportSyncFile(String json) {
        try {
            if (json == null || json.getBytes(StandardCharsets.UTF_8).length > MAX_SYNC_BYTES) {
                throw new IllegalArgumentException("The sync file exceeds 32 MB.");
            }
            JSONObject document = new JSONObject(json);
            if (!"freetarget-portable-sync".equals(document.optString("format"))
                    || document.optInt("schema", -1) != 1) {
                throw new IllegalArgumentException("The sync data has an unsupported format.");
            }
        } catch (JSONException | IllegalArgumentException error) {
            reportSyncExport(false, error.getMessage());
            return;
        }
        runOnUiThread(() -> {
            if (syncPickerOpen) {
                reportSyncExport(false, "Another sync file operation is already open.");
                return;
            }
            pendingSyncExport = json;
            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("application/json");
            intent.putExtra(Intent.EXTRA_TITLE, "freETarget-sync.json");
            try {
                syncPickerOpen = true;
                startActivityForResult(intent, REQUEST_SYNC_EXPORT);
            } catch (RuntimeException error) {
                syncPickerOpen = false;
                pendingSyncExport = null;
                reportSyncExport(false, "Could not open the save dialog: " + error.getMessage());
            }
        });
    }

    private void importSyncFile() {
        runOnUiThread(() -> {
            if (syncPickerOpen) {
                reportSyncImport(null, "Another sync file operation is already open.");
                return;
            }
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("application/json");
            try {
                syncPickerOpen = true;
                startActivityForResult(intent, REQUEST_SYNC_IMPORT);
            } catch (RuntimeException error) {
                syncPickerOpen = false;
                reportSyncImport(null, "Could not open the file picker: " + error.getMessage());
            }
        });
    }

    private static byte[] readLimited(InputStream input, int limit) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int total = 0, count;
        while ((count = input.read(buffer)) != -1) {
            total += count;
            if (total > limit) throw new IOException("The sync file exceeds 32 MB.");
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }

    private void reportSyncExport(boolean success, String message) {
        if (view == null) return;
        String script = "window.FTPortableSync && window.FTPortableSync.exportResult("
                + success + "," + JSONObject.quote(message) + ")";
        view.post(() -> {
            if (view != null) view.evaluateJavascript(script, null);
        });
    }

    private void reportSyncImport(String json, String error) {
        if (view == null) return;
        String script = error != null
                ? "window.FTPortableSync && window.FTPortableSync.importResult(null,"
                        + JSONObject.quote(error) + ")"
                : "window.FTPortableSync && window.FTPortableSync.importResult("
                        + JSONObject.quote(json) + ",null)";
        view.post(() -> {
            if (view != null) view.evaluateJavascript(script, null);
        });
    }

    final class TargetApi {
        @JavascriptInterface public void exportSyncFile(String json) {
            MainActivity.this.exportSyncFile(json);
        }

        @JavascriptInterface public void importSyncFile() {
            MainActivity.this.importSyncFile();
        }

        @JavascriptInterface public void setNavigationAppearance(boolean dark, String sidebarColor) {
            int color = Color.WHITE;
            if (dark) {
                color = sidebarColor != null && sidebarColor.matches("#[0-9a-fA-F]{6}")
                        ? Color.parseColor(sidebarColor) : Color.rgb(20, 34, 53);
            }
            final int background = color;
            runOnUiThread(() -> {
                if (isDestroyed()) return;
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O && !dark) {
                    getWindow().setNavigationBarColor(Color.rgb(32, 42, 54));
                } else {
                    getWindow().setNavigationBarColor(background);
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    WindowInsetsController controller = getWindow().getInsetsController();
                    if (controller != null) {
                        int lightNav = WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
                        controller.setSystemBarsAppearance(dark ? 0 : lightNav, lightNav);
                    }
                } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    View decor = getWindow().getDecorView();
                    int flags = decor.getSystemUiVisibility();
                    int lightNav = View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                    decor.setSystemUiVisibility(dark ? flags & ~lightNav : flags | lightNav);
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
