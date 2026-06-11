(function () {
  function isLoggedIn() {
    return Boolean(
      window.MyHerzenAuth &&
      typeof window.MyHerzenAuth.getToken === "function" &&
      window.MyHerzenAuth.getToken()
    );
  }

  function setHidden(elements, hidden) {
    Array.prototype.forEach.call(elements, function (element) {
      element.hidden = hidden;
    });
  }

  function updateAuthNav() {
    var guestLinks = document.querySelectorAll('[data-auth-link="guest"]');
    var accountLinks = document.querySelectorAll('[data-auth-link="account"]');
    var loggedIn = isLoggedIn();

    setHidden(guestLinks, loggedIn);
    setHidden(accountLinks, !loggedIn);
  }

  window.MyHerzenNav = {
    updateAuthNav: updateAuthNav
  };

  document.addEventListener("DOMContentLoaded", updateAuthNav);

  window.addEventListener("storage", function (event) {
    if (event.key === "myherzen_auth_token") {
      updateAuthNav();
    }
  });
})();
