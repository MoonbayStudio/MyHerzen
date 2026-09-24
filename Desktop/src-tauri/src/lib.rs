// Desktop shell for the MyHerzen web client.
//
// The window hosts the published site, so the desktop build never drifts from the
// web one. Everything that only makes sense in a browser — the marketing header,
// the cookie banner, the WebKit context menu — is removed before the page paints,
// and any navigation that leaves the app area is handed to the system browser.

use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

const START_URL: &str = "https://myherzen.moonbaystudio.ru/app/";

/// Paths that belong to the application itself. Everything else is a website page.
const IN_APP_PATHS: [&str; 3] = ["/app", "/account", "/verify-email"];

/// Runs before every document. Strips the website chrome and browser affordances.
const SHELL_SCRIPT: &str = r#"
(function () {
  if (location.origin !== "https://myherzen.moonbaystudio.ru") return;
  var OUTSIDE = ["/download", "/news", "/support", "/contacts", "/terms", "/privacy", "/cookies", "/api"];

  // The desktop build ships no analytics, so record the narrowest consent and
  // keep the banner from ever rendering.
  try {
    if (!localStorage.getItem("moonbay_cookie_consent_v1")) {
      localStorage.setItem("moonbay_cookie_consent_v1", JSON.stringify({
        necessary: true, analytics: false, marketing: false, updatedAt: new Date().toISOString()
      }));
    }
  } catch (error) {}

  function injectStyle() {
    if (!document.head || document.getElementById("myherzen-desktop-style")) return;
    var style = document.createElement("style");
    style.id = "myherzen-desktop-style";
    style.textContent = ".cookie-banner { display: none !important; }";
    document.head.appendChild(style);
  }

  // /app/ is already an application shell. Pages that still carry the website
  // header — /account/ for instance — lose their marketing links here.
  function pruneNav() {
    var nav = document.querySelector(".top-nav");
    if (!nav) return false;
    var links = nav.querySelectorAll("a[href]");
    for (var i = 0; i < links.length; i++) {
      var path = new URL(links[i].getAttribute("href"), document.baseURI).pathname;
      for (var j = 0; j < OUTSIDE.length; j++) {
        if (path.indexOf(OUTSIDE[j]) === 0) { links[i].hidden = true; break; }
      }
    }
    return true;
  }

  // The context menu would otherwise offer Back/Forward/Stop/Reload in English.
  document.addEventListener("contextmenu", function (event) { event.preventDefault(); });

  injectStyle();
  document.addEventListener("DOMContentLoaded", function () {
    injectStyle();
    if (!pruneNav()) return;
    new MutationObserver(pruneNav).observe(document.body, { childList: true, subtree: true });
  });
})();
"#;

fn stays_in_app(url: &tauri::Url) -> bool {
    if url.scheme() == "tauri" || url.scheme() == "http" && url.host_str() == Some("tauri.localhost")
    {
        return true;
    }
    if url.scheme() != "https"
        || url.host_str() != Some("myherzen.moonbaystudio.ru")
        || url.port_or_known_default() != Some(443)
    {
        return false;
    }
    let path = url.path();
    IN_APP_PATHS
        .iter()
        .any(|prefix| path == *prefix || path.starts_with(&format!("{prefix}/")))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default();

    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }));
    }

    builder
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .setup(|app| {
            let handle = app.handle().clone();
            WebviewWindowBuilder::new(
                app,
                "main",
                WebviewUrl::External(START_URL.parse().expect("стартовый URL")),
            )
            .title("Мой Герцена")
            .inner_size(1180.0, 820.0)
            .min_inner_size(380.0, 540.0)
            .center()
            .initialization_script(SHELL_SCRIPT)
            .on_navigation(move |url| {
                if stays_in_app(url) {
                    return true;
                }
                // Website and third-party pages belong in the user's browser.
                if matches!(url.scheme(), "http" | "https" | "mailto") {
                    let _ = tauri_plugin_opener::OpenerExt::opener(&handle)
                        .open_url(url.as_str(), None::<&str>);
                }
                false
            })
            .on_new_window({
                let handle = app.handle().clone();
                move |url, _features| {
                    if matches!(url.scheme(), "http" | "https" | "mailto") {
                        let _ = tauri_plugin_opener::OpenerExt::opener(&handle)
                            .open_url(url.as_str(), None::<&str>);
                    }
                    tauri::webview::NewWindowResponse::Deny
                }
            })
            .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("не удалось запустить «Мой Герцена»");
}

#[cfg(test)]
mod tests {
    use super::stays_in_app;

    #[test]
    fn only_app_pages_on_the_exact_site_stay_in_the_window() {
        for url in [
            "https://myherzen.moonbaystudio.ru/app/",
            "https://myherzen.moonbaystudio.ru/account/",
            "https://myherzen.moonbaystudio.ru/verify-email/",
        ] {
            assert!(stays_in_app(&url.parse().unwrap()), "{url}");
        }
        for url in [
            "https://myherzen.moonbaystudio.ru/download/",
            "https://myherzen.moonbaystudio.ru.evil.example/app/",
            "http://myherzen.moonbaystudio.ru/app/",
            "https://myherzen.moonbaystudio.ru:444/app/",
            "https://other.example/app/",
        ] {
            assert!(!stays_in_app(&url.parse().unwrap()), "{url}");
        }
    }
}
