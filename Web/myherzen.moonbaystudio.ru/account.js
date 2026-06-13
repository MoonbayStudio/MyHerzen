(function () {
  var auth = window.MyHerzenAuth;
  if (!auth) {
    return;
  }

  var messageEl = document.getElementById("authMessage");
  var loggedOutStateEl = document.getElementById("loggedOutState");
  var loggedInStateEl = document.getElementById("loggedInState");
  var loginForm = document.getElementById("loginForm");
  var registerForm = document.getElementById("registerForm");
  var loginAppleButton = document.getElementById("loginAppleButton");
  var registerAppleButton = document.getElementById("registerAppleButton");
  var loginGoogleButton = document.getElementById("loginGoogleButton");
  var registerGoogleButton = document.getElementById("registerGoogleButton");
  var logoutButton = document.getElementById("logoutButton");

  var loginEmailEl = document.getElementById("loginEmail");
  var loginPasswordEl = document.getElementById("loginPassword");
  var registerNameEl = document.getElementById("registerName");
  var registerEmailEl = document.getElementById("registerEmail");
  var registerPasswordEl = document.getElementById("registerPassword");

  var displayNameEl = document.getElementById("profileDisplayName");
  var emailEl = document.getElementById("profileEmail");
  var userIdEl = document.getElementById("profileUserId");

  function setMessage(text, type) {
    if (!messageEl) {
      return;
    }

    messageEl.textContent = text;
    messageEl.className = "auth-message";

    if (type === "error") {
      messageEl.classList.add("is-error");
    } else if (type === "success") {
      messageEl.classList.add("is-success");
    }
  }

  function updateNav() {
    if (
      window.MyHerzenNav &&
      typeof window.MyHerzenNav.updateAuthNav === "function"
    ) {
      window.MyHerzenNav.updateAuthNav();
    }
  }

  function setLoading(button, isLoading, loadingText) {
    if (!button) {
      return;
    }

    if (isLoading) {
      button.dataset.defaultText = button.textContent;
      button.textContent = loadingText;
      button.disabled = true;
      return;
    }

    button.textContent = button.dataset.defaultText || button.textContent;
    button.disabled = false;
  }

  function setAppleButtonsDisabled(disabled) {
    [loginAppleButton, registerAppleButton].forEach(function (button) {
      if (button) {
        button.disabled = disabled;
      }
    });
  }

  function setGoogleButtonsDisabled(disabled) {
    [loginGoogleButton, registerGoogleButton].forEach(function (button) {
      if (button) {
        if ("disabled" in button) {
          button.disabled = disabled;
        }
        var fallbackButton = button.querySelector ? button.querySelector("button") : null;
        if (fallbackButton) {
          fallbackButton.disabled = disabled;
        }
        button.classList.toggle("is-disabled", disabled);
        button.setAttribute("aria-disabled", disabled ? "true" : "false");
      }
    });
  }

  function setGoogleSlotFallback(slot, label, disabled) {
    if (!slot) {
      return;
    }

    slot.innerHTML = "";
    slot.classList.toggle("is-disabled", !!disabled);
    slot.setAttribute("aria-disabled", disabled ? "true" : "false");

    var button = document.createElement("button");
    button.type = "button";
    button.className = "button secondary google-button google-fallback-button";
    button.textContent = label;
    button.disabled = !!disabled;
    button.addEventListener("click", function () {
      handleGoogleLogin(button);
    });

    slot.appendChild(button);
  }

  async function handleGoogleCredentialResponse(response) {
    try {
      if (!response || typeof response.credential !== "string") {
        throw new Error("missing_google_credential");
      }

      setGoogleButtonsDisabled(true);
      setMessage("Выполняем вход через Google...");
      await auth.handleGoogleCredential(response.credential);
      var user = await auth.fetchCurrentUser();
      renderLoggedIn(user);
    } catch (error) {
      console.error(error);
      setMessage("Не удалось войти через Google.", "error");
    } finally {
      setGoogleButtonsDisabled(false);
    }
  }

  function renderGoogleSlot(slot, options) {
    if (!slot) {
      return true;
    }

    var fallbackLabel = options && options.fallbackLabel ? options.fallbackLabel : "Войти через Google";
    var loadingLabel = slot.dataset.loadingLabel || "Google Login загружается...";

    setGoogleSlotFallback(slot, loadingLabel, true);

    if (
      typeof auth.renderGoogleButton !== "function" ||
      typeof auth.isGoogleAuthAvailable !== "function" ||
      !auth.isGoogleAuthAvailable()
    ) {
      return false;
    }

    var rendered = auth.renderGoogleButton(
      slot,
      handleGoogleCredentialResponse,
      { text: options && options.text ? options.text : "signin_with" }
    );

    if (!rendered) {
      setGoogleSlotFallback(slot, fallbackLabel, false);
      return false;
    }

    window.setTimeout(function () {
      if (slot.children.length === 0) {
        setGoogleSlotFallback(slot, fallbackLabel, false);
      }
    }, 1200);

    return true;
  }

  function renderGoogleButtons() {
    var loginReady = renderGoogleSlot(loginGoogleButton, {
      text: "signin_with",
      fallbackLabel: "Войти через Google"
    });
    var registerReady = renderGoogleSlot(registerGoogleButton, {
      text: "signup_with",
      fallbackLabel: "Зарегистрироваться через Google"
    });

    return loginReady && registerReady;
  }

  function renderLoggedOut(message, type) {
    if (loggedOutStateEl) {
      loggedOutStateEl.hidden = false;
    }
    if (loggedInStateEl) {
      loggedInStateEl.hidden = true;
    }

    if (displayNameEl) {
      displayNameEl.textContent = "—";
    }
    if (emailEl) {
      emailEl.textContent = "—";
    }
    if (userIdEl) {
      userIdEl.textContent = "—";
    }

    setMessage(message || "Вы не вошли в аккаунт.", type || "info");
    updateNav();
  }

  function renderLoggedIn(user) {
    if (displayNameEl) {
      displayNameEl.textContent = user && user.displayName ? user.displayName : "—";
    }
    if (emailEl) {
      emailEl.textContent = user && user.email ? user.email : "—";
    }
    if (userIdEl) {
      userIdEl.textContent = user && user.id ? user.id : "—";
    }

    if (loggedOutStateEl) {
      loggedOutStateEl.hidden = true;
    }
    if (loggedInStateEl) {
      loggedInStateEl.hidden = false;
    }

    setMessage("Профиль загружен.", "success");
    updateNav();
  }

  async function handleAuthResult(result, fallbackMessage) {
    if (result && result.ok) {
      if (result.user) {
        renderLoggedIn(result.user);
      } else {
        await restoreSession();
      }
      return;
    }

    setMessage(result && result.message ? result.message : fallbackMessage, "error");
  }

  async function restoreSession() {
    if (typeof auth.initAppleAuth === "function") {
      auth.initAppleAuth();
    }
    setAppleButtonsDisabled(false);

    renderGoogleButtons();

    var token = auth.getToken();
    if (!token) {
      var methods = ["почте", "регистрацию"];
      methods.push("Apple");
      methods.push("Google");

      var msg = "Выберите вход по " + methods.join(", ") + ".";
      renderLoggedOut(msg);
      return;
    }

    setMessage("Проверяем сессию...");

    try {
      var user = await auth.fetchCurrentUser();
      if (user) {
        renderLoggedIn(user);
        return;
      }

      renderLoggedOut("Сессия истекла. Войдите снова.");
    } catch (error) {
      console.error(error);
      renderLoggedOut("Не удалось загрузить профиль. Попробуйте позже.", "error");
    }
  }

  async function handleAppleLogin(button) {
    try {
      setLoading(button, true, "Открываем Apple...");
      var result = await auth.loginWithApple();
      await handleAuthResult(result, "Не удалось выполнить вход через Apple.");
    } catch (error) {
      console.error(error);
      setMessage("Не удалось начать вход через Apple. Попробуйте позже.", "error");
    } finally {
      setLoading(button, false);
    }
  }

  async function handleGoogleLogin(button) {
    try {
      setLoading(button, true, "Открываем Google...");
      var result = await auth.loginWithGoogle();
      await handleAuthResult(result, "Не удалось выполнить вход через Google.");
    } catch (error) {
      console.error(error);
      setMessage("Не удалось начать вход через Google.", "error");
    } finally {
      setLoading(button, false);
    }
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      var submitButton = loginForm.querySelector('button[type="submit"]');

      try {
        setLoading(submitButton, true, "Входим...");
        var result = await auth.loginWithEmail(loginEmailEl.value, loginPasswordEl.value);
        await handleAuthResult(result, "Не удалось выполнить вход.");
      } finally {
        setLoading(submitButton, false);
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      var submitButton = registerForm.querySelector('button[type="submit"]');

      try {
        setLoading(submitButton, true, "Создаём...");
        var result = await auth.registerWithEmail(
          registerNameEl.value,
          registerEmailEl.value,
          registerPasswordEl.value
        );
        await handleAuthResult(result, "Не удалось создать аккаунт.");
      } finally {
        setLoading(submitButton, false);
      }
    });
  }

  if (loginAppleButton) {
    loginAppleButton.addEventListener("click", function () {
      handleAppleLogin(loginAppleButton);
    });
  }

  if (registerAppleButton) {
    registerAppleButton.addEventListener("click", function () {
      handleAppleLogin(registerAppleButton);
    });
  }

  if (logoutButton) {
    logoutButton.addEventListener("click", function () {
      auth.logout();
      renderLoggedOut("Вы вышли из аккаунта.", "success");
      updateNav();
    });
  }

  restoreSession();

  if (
    typeof auth.isGoogleAuthAvailable === "function" &&
    typeof auth.isAppleAuthAvailable === "function" &&
    (!auth.isGoogleAuthAvailable() || !auth.isAppleAuthAvailable())
  ) {
    var providerLoadAttempts = 0;
    var providerLoadTimer = window.setInterval(function () {
      providerLoadAttempts += 1;

      if (
        (auth.isGoogleAuthAvailable() && auth.isAppleAuthAvailable()) ||
        providerLoadAttempts >= 20
      ) {
        window.clearInterval(providerLoadTimer);
        restoreSession();
      }
    }, 250);
  }
})();
