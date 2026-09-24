(function (root, factory) {
  var core = factory();
  if (typeof module === "object" && module.exports) module.exports = core;
  else root.MyHerzenClient = core;
})(typeof window === "object" ? window : this, function () {
  "use strict";
  var config = Object.freeze({ apiBase: "https://api.myherzen.moonbaystudio.ru", schedulePath: "/university/schedule/v1", aiEnabled: false, defaultCacheWeeks: 2 });
  var resources = ["faculties", "groups", "schedule", "teachers", "rooms", "buildings"];
  var prefix = "myherzen.public.v1:";

  function errorMessage(error) {
    var detail = error && error.data && error.data.detail;
    if (error && error.status === 401) return "Сессия завершена. Войдите в аккаунт снова.";
    if (error && error.status === 403) return "Для этого действия недостаточно прав.";
    if (error && error.status === 409) return "Группа меняется через заявку модератору.";
    if (error && error.status === 429) return "Слишком много запросов. Повторите немного позже.";
    if (error && error.status === 422) return "Проверьте заполненные поля.";
    if (error && error.status >= 500) return "Сервис временно недоступен. Повторите попытку позже.";
    if (error && (error.message === "Failed to fetch" || error.name === "AbortError")) return "Нет связи с сервером. Проверьте подключение и повторите попытку.";
    return typeof detail === "string" ? detail : (error && error.message) || "Не удалось выполнить запрос.";
  }
  function addDays(day, count) {
    var date = new Date(day + "T12:00:00Z");
    if (Number.isNaN(date.getTime())) throw new Error("Некорректная дата");
    date.setUTCDate(date.getUTCDate() + count);
    return date.toISOString().slice(0, 10);
  }
  function today() {
    return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Moscow", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  }
  function time(iso) { return new Intl.DateTimeFormat("ru-RU", { timeZone: "Europe/Moscow", hour: "2-digit", minute: "2-digit" }).format(new Date(iso)); }
  function roles(user) {
    return (user && user.roles || []).map(function (r) { return typeof r === "string" ? r : (r.type || r.key || r.code || r.role || r.name || ""); });
  }
  function permissions(user) {
    var values = roles(user);
    var admin = values.some(function (r) { return ["admin", "owner", "developer"].includes(r); });
    var moderator = admin || values.includes("moderator");
    return { admin: admin, moderator: moderator, editHomework: moderator || values.includes("group_leader") || values.includes("leader") };
  }
  function createClient(options) {
    var fetcher = options.fetch;
    var storage = options.storage;
    var auth = options.auth;
    var pending = new Map();
    function stored(key) { try { return JSON.parse(storage.getItem(key)); } catch (_) { return null; } }
    function save(key, value) {
      try {
        storage.setItem(key, JSON.stringify(value));
        var keys = Object.keys(storage).filter(function (k) { return k.startsWith(prefix); });
        keys.sort(function (a, b) { return ((stored(a) || {}).at || 0) - ((stored(b) || {}).at || 0); });
        while (keys.length > 48) storage.removeItem(keys.shift());
      } catch (_) { /* Storage quota/private browsing: online data remains usable. */ }
    }
    async function publicResource(resource, params, useCache) {
      if (!resources.includes(resource)) throw new Error("Недопустимый ресурс расписания");
      var query = new URLSearchParams(params || {}).toString();
      var path = config.schedulePath + "/" + resource + (query ? "?" + query : "");
      var key = prefix + path;
      var cached = useCache !== false ? stored(key) : null;
      var ttl = resource === "schedule" ? 120000 : 3600000;
      if (cached && Date.now() - cached.at < ttl && Array.isArray(cached.rows)) return { rows: cached.rows, offline: false, cached: true, at: cached.at };
      if (pending.has(path)) return pending.get(path);
      var task = (async function () {
        var controller = new AbortController();
        var timeout = setTimeout(function () { controller.abort(); }, 20000);
        try {
          var response = await fetcher(config.apiBase + path, { headers: { Accept: "application/json" }, credentials: "omit", signal: controller.signal });
          if (!response.ok) throw Object.assign(new Error("Не удалось загрузить расписание с сервера"), { status: response.status });
          var rows = await response.json();
          if (!Array.isArray(rows)) throw new Error("Сервер вернул некорректное расписание");
          var result = { rows: rows, offline: false, at: Date.now() };
          if (useCache !== false) save(key, result);
          return result;
        } catch (error) {
          // A prefetched range also covers individual days selected later offline.
          if (!cached && useCache !== false && resource === "schedule" && params.exam_only === "false") {
            Object.keys(storage).filter(function (k) { return k.startsWith(prefix + config.schedulePath + "/schedule?"); }).forEach(function (k) {
              var q = new URLSearchParams(k.split("?")[1]);
              var entry = stored(k);
              if (entry && Array.isArray(entry.rows) && q.get("group_id") === String(params.group_id) && q.get("exam_only") === "false" &&
                  q.get("start_date") <= params.start_date && q.get("end_date") >= params.start_date && (!cached || entry.at > cached.at)) cached = entry;
            });
          }
          if (cached && Array.isArray(cached.rows)) return { rows: cached.rows, offline: true, cached: true, at: cached.at };
          throw error;
        } finally { clearTimeout(timeout); pending.delete(path); }
      })();
      pending.set(path, task);
      return task;
    }
    async function catalog() {
      var data = await Promise.all([publicResource("faculties"), publicResource("groups")]);
      return { faculties: data[0].rows, groups: data[1].rows, offline: data.some(function (x) { return x.offline; }) };
    }
    async function lookup(resource, field, ids) {
      ids = Array.from(new Set(ids.filter(Boolean))).sort(function (a, b) { return a - b; });
      if (!ids.length) return { rows: [], offline: false };
      var params = {}; params[field] = ids.join(",");
      return publicResource(resource, params);
    }
    async function schedule(groupId, date, exams, cacheWeeks) {
      if (!Number.isSafeInteger(Number(groupId)) || Number(groupId) <= 0) throw new Error("Выберите группу");
      var start = exams ? addDays(date, -120) : date;
      var end = exams ? addDays(date, 120) : addDays(date, Math.max(0, Math.min(4, Number(cacheWeeks) || 0)) * 7);
      var result = await publicResource("schedule", { group_id: groupId, start_date: start, end_date: end, exam_only: String(!!exams) }, cacheWeeks > 0);
      var lookups = await Promise.all([
        lookup("teachers", "teacher_ids", result.rows.map(function (x) { return x.teacher_id; })),
        lookup("rooms", "room_ids", result.rows.map(function (x) { return x.room_id; }))
      ]);
      var buildings = await lookup("buildings", "building_ids", lookups[1].rows.map(function (x) { return x.building_id; }));
      function byId(rows) { return new Map(rows.map(function (x) { return [x.id, x]; })); }
      var teachers = byId(lookups[0].rows), rooms = byId(lookups[1].rows), blocks = byId(buildings.rows);
      var rows = result.rows.filter(function (x) { return exams || x.start_time.slice(0, 10) === date; });
      rows.sort(function (a, b) { return a.start_time.localeCompare(b.start_time); });
      return { offline: result.offline || lookups.some(function (x) { return x.offline; }) || buildings.offline, cached: !!result.cached, at: result.at,
        rows: rows.map(function (x) {
          var room = rooms.get(x.room_id) || {};
          return Object.assign({}, x, { time: time(x.start_time) + "-" + time(x.end_time), teacher: (teachers.get(x.teacher_id) || {}).name || "", room: room.name || "", building: (blocks.get(room.building_id) || {}).name || "" });
        }) };
    }
    function api(path, method, body) {
      if (!/^\/(?:me|settings|account|groups|role-requests|group-change-requests|moderation|admin)(?:\/|\?|$)/.test(path)) throw new Error("Недопустимый запрос аккаунта");
      return auth.requestAuthorizedJson(path, { method: method || "GET", body: body });
    }
    function clearScheduleCache() {
      Object.keys(storage).filter(function (key) { return key.startsWith(prefix); }).forEach(function (key) { storage.removeItem(key); });
    }
    return { catalog: catalog, schedule: schedule, publicResource: publicResource, api: api, clearScheduleCache: clearScheduleCache };
  }
  return { config: config, createClient: createClient, errorMessage: errorMessage, addDays: addDays, today: today, time: time, permissions: permissions };
});
