(function () {
  "use strict";
  var core = window.MyHerzenClient, auth = window.MyHerzenAuth;
  var client = core.createClient({ fetch: window.fetch.bind(window), storage: window.localStorage, auth: auth });
  var user = null, settings = { selectedGroupId: null, scheduleCacheWeeks: 2, liveActivityEnabled: true };
  var catalog = { faculties: [], groups: [] }, page = ["settings", "group", "requests", "exams"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "schedule", generation = 0, accountGeneration = 0;
  function $(id) { return document.getElementById(id); }
  function node(tag, text, className) { var el = document.createElement(tag); if (text != null) el.textContent = text; if (className) el.className = className; return el; }
  function message(text, error) { $("workspaceStatus").textContent = text || ""; $("workspaceStatus").hidden = !text; $("workspaceStatus").classList.toggle("is-error", !!error); }
  async function run(action, button) {
    if (button) button.disabled = true;
    try { return await action(); } catch (error) { message(core.errorMessage(error), true); }
    finally { if (button) button.disabled = false; }
  }
  function button(text, action) { var el = node("button", text, "button secondary"); el.type = "button"; el.addEventListener("click", function () { run(action, el); }); return el; }
  // Lesson card layout follows the native client: time, subject, then icon rows.
  var ICONS = {
    type: '<path d="m4 20 4-1 10-10-3-3L5 16l-1 4Z"/><path d="m14.5 6.5 3 3"/>',
    teacher: '<circle cx="12" cy="8" r="3.2"/><path d="M5 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5"/>',
    room: '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
    note: '<path d="M5 4h14v16H5z"/><path d="M8 9h8M8 13h8M8 17h5"/>'
  };
  function metaRow(icon, text) {
    var row = document.createElement("p");
    row.className = "lesson-meta-row";
    row.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + ICONS[icon] + "</svg>";
    row.append(document.createTextNode(text));
    return row;
  }
  function lessonCard(lesson, exams) {
    var el = node("article", null, "workspace-card lesson-card");
    el.append(node("p", (exams ? lesson.start_time.slice(0, 10) + " · " : "") + lesson.time, "lesson-time"));
    el.append(node("h3", lesson.name));
    if (lesson.type) el.append(metaRow("type", lesson.type));
    if (lesson.teacher) el.append(metaRow("teacher", lesson.teacher));
    var place = [lesson.room, lesson.building].filter(Boolean).join(" · ");
    if (place) el.append(metaRow("room", place));
    if (lesson.note) el.append(metaRow("note", lesson.note));
    return el;
  }
  function card(title, text) { var el = node("article", null, "workspace-card"); el.append(node("h3", title)); if (text) el.append(node("p", text)); return el; }
  function option(value, title) { var el = node("option", title); el.value = value; return el; }
  function requireUser() { if (!user) throw new Error("Войдите в аккаунт, чтобы открыть этот раздел."); }
  function currentGroup() { return catalog.groups.find(function (g) { return g.id === Number($("groupSelect").value); }); }
  function confirm(text) {
    $("confirmText").textContent = text;
    $("confirmDialog").returnValue = "cancel";
    $("confirmDialog").showModal();
    return new Promise(function (resolve) { $("confirmDialog").addEventListener("close", function () { resolve($("confirmDialog").returnValue === "confirm"); }, { once: true }); });
  }
  function applySettings(value) {
    settings = value;
    $("cacheWeeks").value = String(Math.max(0, Math.min(4, value.scheduleCacheWeeks)));
    $("liveActivity").checked = value.liveActivityEnabled;
    $("defaultGroupLabel").textContent = value.selectedGroupName || "Основная группа ещё не выбрана.";
  }
  function renderGroups() {
    var previous = $("groupSelect").value || localStorage.getItem("myherzen.viewGroup") || String(settings.selectedGroupId || "");
    var faculty = $("facultySelect").value, query = $("groupSearch").value.trim().toLocaleLowerCase("ru");
    $("groupSelect").replaceChildren(option("", "Выберите группу"));
    catalog.groups.filter(function (g) { return (!faculty || String(g.faculty_id) === faculty) && (!query || g.name.toLocaleLowerCase("ru").includes(query)); })
      .sort(function (a, b) { return a.name.localeCompare(b.name, "ru", { numeric: true }); })
      .forEach(function (g) { $("groupSelect").append(option(g.id, g.name)); });
    $("groupSelect").value = previous;
  }
  async function loadCatalog() {
    catalog = await client.catalog();
    $("facultySelect").replaceChildren(option("", "Все институты"));
    catalog.faculties.forEach(function (f) { $("facultySelect").append(option(f.id, f.name)); });
    renderGroups();
    if (catalog.offline) message("Список групп из офлайн-кэша.");
  }
  async function loadSchedule() {
    var group = currentGroup();
    var hint = $("noGroupHint");
    if (!group) {
      $("lessons").replaceChildren();
      $("scheduleState").textContent = "";
      if (hint) hint.hidden = false;
      return;
    }
    if (hint) hint.hidden = true;
    var ticket = ++generation, accountTicket = accountGeneration, date = $("scheduleDate").value, exams = page === "exams";
    localStorage.setItem("myherzen.viewGroup", String(group.id));
    $("scheduleState").textContent = "Загружаем расписание…";
    var result;
    try { result = await client.schedule(group.id, date, exams, Number($("cacheWeeks").value)); }
    catch (error) { if (ticket === generation) $("scheduleState").textContent = core.errorMessage(error); return; }
    if (ticket !== generation || accountTicket !== accountGeneration) return;
    var homeworks = [], homeworkError = null;
    if (user && Number(settings.selectedGroupId) === group.id && !exams) {
      try { homeworks = await client.api("/groups/" + group.id + "/homeworks?date=" + encodeURIComponent(date)); }
      catch (error) { homeworkError = core.errorMessage(error); }
    }
    if (ticket !== generation || accountTicket !== accountGeneration) return;
    $("lessons").replaceChildren();
    $("scheduleState").textContent = result.offline || (result.cached && !navigator.onLine) ? "Офлайн: сохранённое расписание от " + new Date(result.at).toLocaleString("ru-RU") : (result.cached ? "Сохранённое расписание от " + new Date(result.at).toLocaleString("ru-RU") : "Расписание обновлено.");
    if (!result.rows.length) $("scheduleState").textContent += exams ? " В выбранном периоде экзаменов нет." : " На выбранную дату занятий нет.";
    if (homeworkError) message("Расписание загружено. Домашние задания: " + homeworkError, true);
    result.rows.forEach(function (lesson) {
      var el = lessonCard(lesson, exams);
      if (lesson.class_url) {
        try { var url = new URL(lesson.class_url); if (url.protocol === "https:") { var link = node("a", "Онлайн-занятие", "button secondary"); link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer"; el.append(link); } } catch (_) {}
      }
      var hw = homeworks.find(function (h) { return h.subject === lesson.name && (!h.lesson_time || h.lesson_time === lesson.time); });
      if (hw) el.append(node("h4", "Домашнее задание"), node("p", hw.text));
      if (user && Number(settings.selectedGroupId) === group.id && core.permissions(user).editHomework && !exams && !homeworkError) {
        var input = node("textarea"); input.value = hw ? hw.text : ""; input.maxLength = 10000; input.setAttribute("aria-label", "Домашнее задание: " + lesson.name);
        el.append(input, button("Сохранить задание", async function () {
          if (!input.value.trim()) throw new Error("Введите текст задания.");
          await client.api("/groups/" + group.id + "/homeworks" + (hw ? "/" + hw.id : ""), hw ? "PATCH" : "POST",
            hw ? { text: input.value.trim() } : { lesson_date: date, lesson_time: lesson.time, subject: lesson.name, teacher: lesson.teacher, room: lesson.room, text: input.value.trim() });
          await loadSchedule();
        }));
        if (hw) el.append(button("Удалить задание", async function () { if (await confirm("Удалить это домашнее задание для всей группы?")) { await client.api("/groups/" + group.id + "/homeworks/" + hw.id, "DELETE"); await loadSchedule(); } }));
      }
      $("lessons").append(el);
    });
  }
  async function loadGroup() {
    // Group picking works for guests too; only the member list needs an account.
    $("groupMembers").replaceChildren();
    if (!user) { $("defaultGroupLabel").textContent = "Войдите в аккаунт, чтобы выбрать основную группу."; return; }
    applySettings(await auth.getSettings());
    if (!settings.selectedGroupId) return;
    var ticket = accountGeneration;
    var members = await client.api("/groups/" + settings.selectedGroupId + "/users");
    if (ticket !== accountGeneration) return;
    members.forEach(function (member) { $("groupMembers").append(card(member.displayName || member.name || "Участник", (member.roles || []).map(function (r) { return r.title || r.type; }).join(", "))); });
  }
  async function setDefaultGroup() {
    requireUser(); var group = currentGroup(); if (!group) throw new Error("Сначала выберите группу в разделе «Пары».");
    var fresh = await auth.getSettings();
    var changes = fresh.selectedGroupId != null && Number(fresh.selectedGroupId) !== group.id;
    if (!await confirm(changes ? "Отправить модератору заявку на смену основной группы на «" + group.name + "»?" : "Привязать аккаунт к группе «" + group.name + "»? Дальнейшая смена — через модератора.")) return;
    if (changes) { await client.api("/group-change-requests", "POST", { requestedGroupId: group.id, requestedGroupName: group.name }); message("Заявка на смену группы отправлена."); }
    else { applySettings(await auth.updateSettings({ selectedGroupId: group.id, selectedGroupName: group.name })); message("Основная группа сохранена."); }
    await loadGroup();
  }
  async function loadRequests() {
    $("roleRequests").replaceChildren(); $("groupRequests").replaceChildren(); requireUser();
    var ticket = accountGeneration;
    var results = await Promise.all([client.api("/role-requests/me"), client.api("/group-change-requests/me")]);
    if (ticket !== accountGeneration) return;
    results.forEach(function (rows, index) {
      var container = $(index ? "groupRequests" : "roleRequests");
      if (!rows.length) container.append(node("p", "Заявок нет."));
      rows.forEach(function (r) {
        var roleNames = { group_leader: "Староста", moderator: "Модератор", student: "Студент", tester: "Тестировщик", plus: "Plus", premium: "Premium" };
        var statuses = { pending: "На рассмотрении", approved: "Одобрена", rejected: "Отклонена", cancelled: "Отменена" };
        var role = r.requestedRole || r.roleType;
        var el = card(index ? r.requestedGroupName || "Смена группы" : roleNames[role] || role, "Статус: " + (statuses[r.status] || r.status) + (r.reviewComment ? "\n" + r.reviewComment : ""));
        if (r.status === "pending") el.append(button("Отменить заявку", async function () { await client.api((index ? "/group-change-requests/" : "/role-requests/") + r.id + "/cancel", "POST"); await loadRequests(); }));
        container.append(el);
      });
    });
  }
  function renderSessions(rows, container, admin) {
    container.replaceChildren();
    rows.filter(function (s) { return !s.revokedAt; }).forEach(function (s) {
      var el = card((s.deviceName || s.platform || "Устройство") + (s.isCurrent ? " · текущее" : ""), [s.lastSeenAt, s.maskedIp].filter(Boolean).join(" · "));
      el.append(button("Завершить сеанс", async function () {
        if (!await confirm("Завершить сеанс на устройстве «" + (s.deviceName || s.platform || "Устройство") + "»?")) return;
        await client.api(admin ? "/admin/sessions/" + s.id + "/revoke" : "/account/sessions/" + s.id, admin ? "POST" : "DELETE");
        if (s.isCurrent && !admin) { auth.logout(); await refreshAccount(); } else if (!admin) await loadSessions(); else el.remove();
      }));
      container.append(el);
    });
    if (!container.children.length) container.append(node("p", "Активных сеансов нет."));
  }
  async function loadSessions() {
    $("sessions").replaceChildren(); $("logoutOthers").hidden = !user;
    if (!user) { $("sessions").append(node("p", "Войдите для просмотра устройств.")); return; }
    var ticket = accountGeneration, rows = await client.api("/account/sessions");
    if (ticket === accountGeneration) renderSessions(rows, $("sessions"), false);
  }
  var ROW_ICONS = {
    security: '<path d="M12 3 5 6v6c0 4.2 2.9 7.9 7 9 4.1-1.1 7-4.8 7-9V6l-7-3Z"/>',
    group: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5 6-5s6 1.7 6 5"/><path d="M16 5.5a3 3 0 0 1 0 5.6M18 20c0-2.6-1-4.2-2.6-5"/>',
    requests: '<path d="M5 4h14v16l-7-3.5L5 20V4Z"/>',
    admin: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.2 5.2l2.1 2.1M16.7 16.7l2.1 2.1M18.8 5.2l-2.1 2.1M7.3 16.7l-2.1 2.1"/>',
    logout: '<path d="M15 5H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h9"/><path d="m14 15 4-3-4-3M18 12H9"/>',
    devices: '<rect x="3" y="5" width="13" height="10" rx="2"/><path d="M2 19h14"/><rect x="17" y="9" width="5" height="10" rx="1.5"/>',
    login: '<path d="M9 5h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9"/><path d="m10 15-4-3 4-3M6 12h9"/>'
  };
  var CHEVRON = '<svg class="app-row-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>';
  function accountRow(icon, text, action, chevron) {
    var el = document.createElement(action && action.href ? "a" : "button");
    el.className = "app-row";
    el.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + ROW_ICONS[icon] + "</svg>";
    var label = document.createElement("span");
    label.textContent = text;
    el.append(label);
    if (chevron !== false) el.insertAdjacentHTML("beforeend", CHEVRON);
    if (action && action.href) el.href = action.href;
    else if (action && action.page) el.addEventListener("click", function () { run(function () { return showPage(action.page); }); });
    else if (action && action.run) el.addEventListener("click", action.run);
    return el;
  }
  // Account section: profile card plus the rows the native client shows.
  function renderAccountPage() {
    var card = $("profileCard"), rows = $("accountRows");
    if (!card || !rows) return;
    rows.replaceChildren();
    card.hidden = !user;
    if (!user) {
      rows.append(accountRow("login", "Войти или зарегистрироваться", { href: "account/" }));
      return;
    }
    $("profileAvatar").textContent = (user.displayName || user.email || "?").trim().charAt(0).toUpperCase();
    $("profileName").textContent = user.displayName || user.email || "Аккаунт";
    var badges = $("profileBadges");
    badges.replaceChildren();
    (user.roles || []).forEach(function (role) { if (role.title) badges.append(node("span", role.title, "app-badge")); });
    if (settings.selectedGroupName) badges.append(node("span", settings.selectedGroupName, "app-badge is-group"));
    rows.append(accountRow("security", "Профиль, почта и пароль", { href: "account/" }));
    rows.append(accountRow("devices", "Активные устройства", { page: "sessions" }));
    rows.append(accountRow("group", "Моя группа", { page: "group" }));
    rows.append(accountRow("requests", "Заявки", { page: "requests" }));
    if (core.permissions(user).moderator) rows.append(accountRow("admin", "Управление", { page: "admin" }));
    rows.append(accountRow("logout", "Выйти из аккаунта", { run: function () { auth.logout(); } }, false));
  }
  // Sidebar account block: avatar initial, display name and the highest role.
  function renderAccountBlock() {
    var avatar = $("accountAvatar"), name = $("accountName"), role = $("accountRole");
    if (!avatar || !name || !role) return;
    if (!user) {
      avatar.textContent = "?"; name.textContent = "Аккаунт"; role.textContent = "Вход не выполнен";
      return;
    }
    var label = user.displayName || user.email || "Аккаунт";
    avatar.textContent = label.trim().charAt(0).toUpperCase() || "?";
    name.textContent = label;
    var titles = (user.roles || []).map(function (item) { return item.title; }).filter(Boolean);
    role.textContent = titles.length ? titles.join(" · ") : "Студент";
  }
  async function refreshAccount() {
    var ticket = ++accountGeneration; user = null;
    ["groupMembers", "roleRequests", "groupRequests", "sessions", "adminContent", "lessons"].forEach(function (id) { $(id).replaceChildren(); });
    $("adminTab").hidden = true;
    applySettings({ selectedGroupId: null, scheduleCacheWeeks: Number(localStorage.getItem("myherzen.guestWeeks") || 2), liveActivityEnabled: true });
    if (auth.getToken()) {
      try {
        var result = await Promise.all([auth.fetchCurrentUser(), auth.getSettings()]);
        if (ticket !== accountGeneration) return;
        user = result[0]; applySettings(result[1]); $("adminTab").hidden = !core.permissions(user).moderator;
      } catch (error) { if (ticket === accountGeneration) message(core.errorMessage(error), true); }
    }
    if (ticket !== accountGeneration) return;
    renderAccountBlock();
    renderGroups();
    if (page === "admin" && !core.permissions(user).moderator) page = "schedule";
    await showPage(page);
  }
  var ROOT_PAGES = ["schedule", "exams", "admin", "menu", "account"];
  var backTarget = null;
  async function showPage(next) {
    var previous = page;
    if (ROOT_PAGES.indexOf(next) === -1) {
      if (ROOT_PAGES.indexOf(previous) !== -1) backTarget = previous;
    } else backTarget = null;
    var back = $("backButton");
    if (back) back.hidden = !backTarget;
    page = next; generation++;
    document.querySelectorAll("[data-page]").forEach(function (el) { var active = el.dataset.page === page; el.classList.toggle("primary", active); el.classList.toggle("secondary", !active); if (active) el.setAttribute("aria-current", "page"); else el.removeAttribute("aria-current"); });
    ["schedule", "group", "requests", "settings", "admin", "menu", "about", "account", "themes", "accessibility", "sessions"].forEach(function (name) { $(name + "Page").hidden = name !== (page === "exams" ? "schedule" : page); });
    var controls = $("scheduleControls");
    if (controls) controls.hidden = page !== "schedule" && page !== "exams";
    var tab = document.querySelector('[data-page="' + page + '"]');
    var heading = $("appPageTitle");
    if (heading) heading.textContent = tab && tab.dataset.title ? tab.dataset.title : "Расписание";
    var legacyTitle = $("scheduleTitle");
    if (legacyTitle) legacyTitle.textContent = page === "exams" ? "Сессия: экзамены и зачёты" : "Расписание";
    if (page === "schedule" || page === "exams") await loadSchedule();
    if (page === "group") await loadGroup();
    if (page === "requests") await loadRequests();
    if (page === "sessions") await loadSessions();
    if (page === "admin") await loadAdmin();
    if (page === "account") renderAccountPage();
  }
  function field(parent, label, value, type) { var wrap = node("label", label), input = node(type === "textarea" ? "textarea" : "input"); if (type && type !== "textarea") input.type = type; input.value = value == null ? "" : String(value); wrap.append(input); parent.append(wrap); return input; }
  function select(parent, label, values, selected) { var wrap = node("label", label), input = node("select"); values.forEach(function (v) { input.append(option(v[0], v[1])); }); input.value = selected; wrap.append(input); parent.append(wrap); return input; }
  async function loadAdmin() {
    requireUser(); if (!core.permissions(user).moderator) throw new Error("Для этого раздела недостаточно прав.");
    var container = $("adminContent"), section = $("adminSection").value, ticket = accountGeneration; container.replaceChildren();
    if (section === "requests") {
      var datasets = await Promise.all([client.api("/moderation/role-requests"), client.api("/moderation/group-change-requests?status=pending")]);
      if (ticket !== accountGeneration) return;
      datasets.forEach(function (rows, index) { rows.forEach(function (r) {
        var el = card(r.userName || r.userEmail || "Пользователь " + r.userId, index ? "Группа: " + r.requestedGroupName : "Роль: " + (r.requestedRole || r.roleType));
        var comment = field(el, "Комментарий", r.message || r.comment || "", "textarea");
        ["approve", "reject"].forEach(function (action) { el.append(button(action === "approve" ? "Одобрить" : "Отклонить", async function () {
          if (!await confirm("Подтвердить решение по заявке №" + r.id + "?")) return;
          await client.api((index ? "/moderation/group-change-requests/" : "/moderation/role-requests/") + r.id + "/" + action, "POST", { comment: comment.value }); await loadAdmin();
        })); }); container.append(el);
      }); });
    } else if (section === "users") {
      var results = await Promise.all([client.api("/admin/users"), client.api("/admin/badges")]);
      if (ticket !== accountGeneration) return;
      results[0].forEach(function (u) {
        var el = card(u.name || u.email || u.id, (u.roles || []).map(function (r) { return r.title || r.type; }).join(", "));
        var role = select(el, "Роль", [["free", "Free"], ["tester", "Тестировщик"], ["plus", "Plus"], ["premium", "Premium"], ["moderator", "Модератор"], ["admin", "Администратор"]], "free");
        ["grant", "revoke"].forEach(function (action) { el.append(button(action === "grant" ? "Выдать роль" : "Снять роль", async function () {
          if (await confirm("Изменить роль «" + role.value + "» пользователя " + (u.name || u.id) + "?")) { await client.api("/admin/roles/" + action, "POST", { user_id: Number(u.id), role: role.value }); await loadAdmin(); }
        })); });
        var badge = select(el, "Значок", results[1].map(function (b) { return [b.code, b.title]; }), results[1][0] && results[1][0].code);
        el.append(button("Выдать значок", async function () { if (!badge.value) return; await client.api("/admin/users/" + u.id + "/badges", "POST", { badge_code: badge.value }); await loadAdmin(); }));
        (u.badges || []).forEach(function (b) { el.append(button("Снять: " + b.title, async function () { if (await confirm("Снять значок «" + b.title + "»?")) { await client.api("/admin/users/" + u.id + "/badges/" + encodeURIComponent(b.code), "DELETE"); await loadAdmin(); } })); });
        var sessions = node("div"); el.append(button("Показать устройства", async function () { renderSessions(await client.api("/admin/users/" + u.id + "/sessions"), sessions, true); }), sessions); container.append(el);
      });
    } else if (section === "settings") {
      var rows = await client.api("/admin/settings"); if (ticket !== accountGeneration) return;
      (Array.isArray(rows) ? rows : rows.settings).forEach(function (setting) {
        var el = card(setting.key, setting.description || ""); var input = field(el, "Значение (" + setting.valueType + ")", typeof setting.value === "object" ? JSON.stringify(setting.value) : setting.value);
        if (setting.key === "AI_ENABLED") { input.disabled = true; el.append(node("p", "ИИ отключён в этой версии клиентов независимо от серверной настройки.")); }
        else el.append(button("Сохранить", async function () { var value = setting.valueType === "json" ? JSON.parse(input.value) : setting.valueType === "bool" ? input.value === "true" : setting.valueType === "int" ? Number(input.value) : input.value; if (await confirm("Изменить настройку сервиса «" + setting.key + "»?")) { await client.api("/admin/settings/" + encodeURIComponent(setting.key), "PATCH", { value: value }); message("Настройка сохранена."); } })); container.append(el);
      });
    } else {
      var notices = await client.api("/admin/system-notices"); if (ticket !== accountGeneration) return;
      [null].concat(Array.isArray(notices) ? notices : notices.notices).forEach(function (notice) {
        var el = card(notice ? "Объявление №" + notice.id : "Новое объявление"), value = notice || {};
        var title = field(el, "Заголовок", value.title), text = field(el, "Текст", value.message, "textarea");
        var type = select(el, "Тип", [["info", "Информация"], ["warning", "Предупреждение"], ["maintenance", "Техработы"], ["critical", "Важно"]], value.type || "info");
        var showAs = select(el, "Показ", [["banner", "Баннер"], ["modal", "Модальное окно"]], value.showAs || "banner");
        var dismissible = select(el, "Можно закрыть", [["true", "Да"], ["false", "Нет"]], String(value.dismissible !== false));
        var start = field(el, "Начало (ISO 8601, необязательно)", value.startsAt), end = field(el, "Окончание (ISO 8601, необязательно)", value.endsAt);
        el.append(button("Сохранить объявление", async function () { if (!title.value.trim() || !text.value.trim()) throw new Error("Заполните заголовок и текст"); await client.api("/admin/system-notices" + (notice ? "/" + notice.id : ""), notice ? "PATCH" : "POST", { title: title.value, message: text.value, type: type.value, showAs: showAs.value, dismissible: dismissible.value === "true", startsAt: start.value || null, endsAt: end.value || null }); await loadAdmin(); }));
        if (notice) {
          el.append(button(notice.isActive ? "Отключить" : "Активировать", async function () { if (await confirm("Изменить видимость объявления для всех пользователей?")) { await client.api("/admin/system-notices/" + notice.id + (notice.isActive ? "/deactivate" : "/activate"), "POST"); await loadAdmin(); } }));
          el.append(button("Удалить", async function () { if (await confirm("Удалить объявление №" + notice.id + "?")) { await client.api("/admin/system-notices/" + notice.id, "DELETE"); await loadAdmin(); } }));
        } container.append(el);
      });
    }
    if (!container.children.length) container.append(node("p", "Записей нет."));
  }
  async function loadNotice() {
    var response = await fetch(core.config.apiBase + "/system/notice", { credentials: "omit" }); if (!response.ok) return;
    var data = await response.json(), notice = data.notice;
    if (!data.isActive || !notice || (notice.dismissible && sessionStorage.getItem("myherzen.notice") === String(notice.id))) return;
    $("noticeTitle").textContent = notice.title; $("noticeText").textContent = notice.message; $("systemNotice").hidden = false;
    $("dismissNotice").hidden = !notice.dismissible;
    $("dismissNotice").onclick = function () { if (notice.dismissible) { sessionStorage.setItem("myherzen.notice", String(notice.id)); $("systemNotice").hidden = true; } };
    if (notice.showAs === "modal" || notice.show_as === "modal") {
      $("modalNoticeTitle").textContent = notice.title; $("modalNoticeText").textContent = notice.message;
      $("closeModalNotice").hidden = !notice.dismissible;
      $("noticeDialog").oncancel = function (event) { if (!notice.dismissible) event.preventDefault(); else $("dismissNotice").onclick(); };
      $("closeModalNotice").onclick = function () { $("dismissNotice").onclick(); $("noticeDialog").close(); };
      $("noticeDialog").showModal();
    }
  }
  function preferences() {
    var theme = $("webTheme").value;
    document.body.dataset.webTheme = theme === "system" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : theme;
    localStorage.setItem("myherzen.webTheme", theme);
    [["largerText", "largeText"], ["highContrast", "highContrast"], ["reduceMotion", "reduceMotion"]].forEach(function (pair) { document.body.dataset[pair[1]] = String($(pair[0]).checked); localStorage.setItem("myherzen." + pair[0], String($(pair[0]).checked)); });
  }
  document.querySelectorAll("[data-page]").forEach(function (el) { el.addEventListener("click", function () { run(function () { return showPage(el.dataset.page); }, el); }); });
  $("scheduleDate").value = core.today();
  $("facultySelect").onchange = renderGroups; $("groupSearch").oninput = renderGroups;
  $("groupSelect").onchange = function () { run(loadSchedule); };
  $("scheduleDate").onchange = function () { run(loadSchedule); };
  $("refreshSchedule").onclick = function () { run(loadSchedule, this); };
  $("backButton").onclick = function () { var target = backTarget; if (target) run(function () { return showPage(target); }); };
  $("setDefaultGroup").onclick = function () { run(setDefaultGroup, this); };
  $("roleRequestForm").onsubmit = function (event) { event.preventDefault(); run(async function () { requireUser(); await client.api("/role-requests", "POST", { roleType: $("requestedRole").value, groupId: settings.selectedGroupId, groupName: settings.selectedGroupName, comment: $("requestComment").value }); message("Заявка отправлена."); await loadRequests(); }, event.submitter); };
  function saveSettings(control) {
    run(async function () {
      var next = { scheduleCacheWeeks: Number($("cacheWeeks").value), liveActivityEnabled: $("liveActivity").checked };
      if (user) applySettings(await auth.updateSettings(next));
      else { settings = Object.assign({}, settings, next); localStorage.setItem("myherzen.guestWeeks", String(next.scheduleCacheWeeks)); }
      if (!next.scheduleCacheWeeks) client.clearScheduleCache();
      $("settingsState").textContent = user ? "Синхронизировано с аккаунтом." : "Сохранено на этом устройстве.";
    }, control);
  }
  $("cacheWeeks").onchange = function () { saveSettings(this); };
  $("liveActivity").onchange = function () { saveSettings(this); };
  $("clearCache").onclick = function () { client.clearScheduleCache(); message("Локальный кэш расписания удалён. Аккаунт и серверные данные сохранены."); };
  $("logoutOthers").onclick = function () { run(async function () { requireUser(); if (await confirm("Завершить все сеансы аккаунта, кроме текущего?")) { await client.api("/account/sessions/logout-others", "POST"); await loadSessions(); } }, this); };
  $("refreshAdmin").onclick = function () { run(loadAdmin, this); }; $("adminSection").onchange = function () { run(loadAdmin); };
  ["webTheme", "largerText", "highContrast", "reduceMotion"].forEach(function (id) { if (id === "webTheme") $(id).value = localStorage.getItem("myherzen.webTheme") || "system"; else $(id).checked = localStorage.getItem("myherzen." + id) === "true"; $(id).onchange = preferences; }); preferences();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", preferences);
  window.addEventListener("myherzen:logout", function () { run(refreshAccount); });
  window.addEventListener("storage", function (event) { if (event.key === "myherzen_auth_token") run(refreshAccount); });
  window.addEventListener("online", function () { run(loadSchedule); });
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("app-sw.js", { scope: "/app/" }).catch(function () { /* Online use does not depend on worker support. */ });
  run(async function () { await run(loadCatalog); await refreshAccount(); await loadNotice(); });
})();
