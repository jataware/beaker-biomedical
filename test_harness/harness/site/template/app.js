/* CRDC skill eval dashboard — vanilla JS, no dependencies.
 * Reads the inlined report blob (#report-data) and renders three hash-routed
 * views: Results (pass/fail matrix + trace), Skills (read-only doc explorer),
 * Tests (corpus / answer-key explorer). Markdown is pre-rendered at build time;
 * here we only ever set that trusted HTML, and use textContent for trace text. */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("report-data").textContent);
  var APP = document.getElementById("app");

  // -- indexes ------------------------------------------------------------
  var runByUid = {}, groups = {};
  DATA.runs.forEach(function (r) {
    runByUid[r.run_uid] = r;
    var k = r.ref + "|" + r.model;
    (groups[k] = groups[k] || []).push(r);
  });
  Object.keys(groups).forEach(function (k) {
    groups[k].sort(function (a, b) { return a.rep - b.rep; });
  });
  var testByRef = {};
  DATA.tests.forEach(function (t) { testByRef[t.ref] = t; });
  var skillByService = DATA.skills || {};

  var ui = { q: "", status: "all", service: "all", model: "all", expand: false };

  // -- tiny DOM helper ----------------------------------------------------
  function h(tag, props) {
    var e = document.createElement(tag), k;
    if (props) for (k in props) {
      if (k === "class") e.className = props[k];
      else if (k === "html") e.innerHTML = props[k];
      else if (k === "text") e.textContent = props[k];
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2).toLowerCase(), props[k]);
      else if (props[k] != null && props[k] !== false) e.setAttribute(k, props[k]);
    }
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null || c === false) continue;
      if (Array.isArray(c)) c.forEach(function (x) { if (x != null && x !== false) e.append(x); });
      else e.append(c);
    }
    return e;
  }
  function pct(x) { return Math.round((x || 0) * 100) + "%"; }

  // -- router -------------------------------------------------------------
  function hResults(uid) { return "#results" + (uid ? "/" + uid : ""); }
  function hSkills(svc, path) { return "#skills/" + svc + "/" + encodeURIComponent(path); }
  function hTests(ref) { return "#tests/" + encodeURIComponent(ref); }

  function route() {
    var parts = location.hash.replace(/^#/, "").split("/");
    var view = parts[0] || "results";
    if (view === "skills") return { view: "skills", svc: parts[1], path: parts[2] ? decodeURIComponent(parts[2]) : null };
    if (view === "tests") return { view: "tests", ref: parts[1] ? decodeURIComponent(parts[1]) : null };
    return { view: "results", uid: parts[1] || null };
  }
  window.addEventListener("hashchange", render);

  // -- cell status --------------------------------------------------------
  function cellOf(ref, model) { return (DATA.cells || {})[ref + "|" + model]; }
  function cellClass(c) {
    if (!c || !c.total) return "none";
    if (c.pass === c.total) return "pass";
    if (c.pass === 0) return "fail";
    return "partial";
  }
  function cellLabel(c) {
    if (!c || !c.total) return "—";
    if (c.total === 1) return c.pass ? "✓" : "✗";
    return c.pass + "/" + c.total;
  }

  // -- header + tabs ------------------------------------------------------
  function header() {
    var g = DATA.git || {}, cfg = DATA.config || {}, s = DATA.summary || {};
    var chips = [
      g.sha && h("span", { class: "chip" }, h("b", {}, (g.branch || "") + " @" + g.sha) , g.dirty ? " (dirty)" : ""),
      DATA.generated_at && h("span", { class: "chip" }, "built ", h("b", {}, DATA.generated_at)),
      h("span", { class: "chip" }, h("b", {}, String(DATA.models.length)), " model" + (DATA.models.length === 1 ? "" : "s")),
      DATA.judge_model && h("span", { class: "chip" }, "judge ", h("b", {}, DATA.judge_model)),
      (cfg.max_steps != null) && h("span", { class: "chip" }, "temp ", h("b", {}, String(cfg.temperature)), " · max_steps ", h("b", {}, String(cfg.max_steps)))
    ];
    var stats = h("div", { class: "headline" },
      h("div", { class: "stat" }, h("b", {}, s.runs_passed + "/" + s.runs), "runs passed (" + pct(s.run_pass_rate) + ")"),
      h("div", { class: "stat" }, h("b", {}, pct(s.check_pass_rate)), "check pass rate"),
      h("div", { class: "stat" }, h("b", {}, String(s.n_tests)), "tests"),
      h("div", { class: "stat" }, h("b", {}, String((DATA.services || []).length)), "services"));
    return h("header", { class: "top" }, h("h1", {}, "CRDC skill evaluation"),
      h("div", { class: "chips" }, chips), stats);
  }

  function tabs(active) {
    function tab(id, label) {
      return h("button", { class: active === id ? "active" : "", onClick: function () { location.hash = "#" + id; } }, label);
    }
    return h("nav", { class: "tabs" }, tab("results", "Results"),
      tab("skills", "View all skills (read-only)"), tab("tests", "View all tests (read-only)"));
  }

  // -- RESULTS view -------------------------------------------------------
  function orderedTests() {
    var seen = {}, list = [];
    DATA.runs.forEach(function (r) {
      if (seen[r.ref]) return; seen[r.ref] = 1;
      list.push({ ref: r.ref, service: r.service, category: r.category, leaf: r.leaf, title: r.title });
    });
    var svcOrder = {}; (DATA.services || []).forEach(function (s, i) { svcOrder[s] = i; });
    list.sort(function (a, b) {
      return (svcOrder[a.service] - svcOrder[b.service]) ||
        a.category.localeCompare(b.category) || a.leaf.localeCompare(b.leaf);
    });
    return list;
  }

  function rowStatus(ref, models) {
    var pass = 0, total = 0;
    models.forEach(function (m) { var c = cellOf(ref, m); if (c) { pass += c.pass; total += c.total; } });
    if (!total) return "none";
    if (pass === total) return "pass";
    if (pass === 0) return "fail";
    return "partial";
  }

  function controls() {
    var seg = h("div", { class: "seg" }, ["all", "failing", "partial"].map(function (st) {
      return h("button", { class: ui.status === st ? "active" : "", onClick: function () { ui.status = st; render(); } },
        st[0].toUpperCase() + st.slice(1));
    }));
    var svcSel = h("select", { onChange: function (e) { ui.service = e.target.value; render(); } },
      [h("option", { value: "all" }, "all services")].concat((DATA.services || []).map(function (s) {
        return h("option", { value: s, selected: ui.service === s }, s);
      })));
    var modelSel = h("select", { onChange: function (e) { ui.model = e.target.value; render(); } },
      [h("option", { value: "all" }, "all models")].concat(DATA.models.map(function (m) {
        return h("option", { value: m, selected: ui.model === m }, m);
      })));
    var search = h("input", { type: "search", placeholder: "filter tests…", value: ui.q,
      onInput: function (e) { ui.q = e.target.value; render(); } });
    var expand = h("label", { class: "chip" },
      h("input", { type: "checkbox", checked: ui.expand, onChange: function (e) { ui.expand = e.target.checked; render(); } }),
      "expand traces");
    return h("div", { class: "controls" }, search, seg, svcSel, modelSel, expand);
  }

  function resultsView(sel) {
    var models = ui.model === "all" ? DATA.models : [ui.model];
    var q = ui.q.trim().toLowerCase();
    var rows = orderedTests().filter(function (t) {
      if (ui.service !== "all" && t.service !== ui.service) return false;
      if (q && (t.ref + " " + t.title + " " + t.leaf).toLowerCase().indexOf(q) < 0) return false;
      var st = rowStatus(t.ref, models);
      if (ui.status === "failing" && (st === "pass" || st === "none")) return false;
      if (ui.status === "partial" && st !== "partial") return false;
      return true;
    });

    var head = h("tr", {}, h("th", { class: "test" }, "test"),
      models.map(function (m) {
        var pass = 0, total = 0;
        rows.forEach(function (t) { var c = cellOf(t.ref, m); if (c) { pass += c.pass; total += c.total; } });
        var allPass = total > 0 && pass === total;
        return h("th", {},
          h("div", { class: "mname" }, m.split("/").pop()),
          h("div", { class: "mtally" + (allPass ? " allpass" : "") },
            total ? (allPass ? "✓ " : "") + pass + "/" + total : "—"));
      }));
    var body = [], curGroup = null, selKey = null;
    if (sel.uid && runByUid[sel.uid]) { var sr = runByUid[sel.uid]; selKey = sr.ref + "|" + sr.model; }
    rows.forEach(function (t) {
      var gname = t.service + " · " + t.category;
      if (gname !== curGroup) {
        curGroup = gname;
        body.push(h("tr", { class: "group" }, h("td", { colspan: models.length + 1 }, gname)));
      }
      var cells = models.map(function (m) {
        var c = cellOf(t.ref, m), key = t.ref + "|" + m, short = m.split("/").pop();
        return h("td", { class: "cell " + cellClass(c) + (key === selKey ? " sel" : ""),
          title: c ? "view results — " + short : short + " (no run)",
          onClick: c ? function () { location.hash = hResults(c.run_uids[0]); } : null }, cellLabel(c));
      });
      body.push(h("tr", {}, h("td", { class: "test" },
        h("a", { class: "testlink", href: hTests(t.ref),
          title: "view test details and answer key" },
          h("div", { class: "leaf" }, t.leaf),
          h("div", { class: "ttl" }, t.title))), cells));
    });

    var table = rows.length
      ? h("table", { class: "matrix" }, h("thead", {}, head), h("tbody", {}, body))
      : h("div", { class: "empty" }, "No tests match the current filters.");

    var detail = sel.uid && runByUid[sel.uid] ? runDetail(runByUid[sel.uid]) : null;
    return h("div", {}, controls(), table, detail);
  }

  // -- run detail (checks + trace) ---------------------------------------
  function checkRow(c) {
    var st = c.passed === true ? "pass" : c.passed === false ? "fail" : "none";
    var mark = c.passed === true ? "PASS" : c.passed === false ? "FAIL" : "UNSCORED";
    return h("tr", {},
      h("td", { class: "st" }, h("span", { class: "badge lg " + st }, mark)),
      h("td", { class: "fam" }, c.family
        ? h("span", { class: "chip-fam " + c.family }, c.family)
        : (c.method ? h("span", { class: "tag" }, c.method) : null)),
      h("td", { class: "ct" }, h("span", { class: "checktype" }, c.type)),
      h("td", { class: "desired" }, c.spec || ""),
      h("td", { class: "output" }, c.detail || ""));
  }

  function checksTable(checks) {
    return h("table", { class: "checks rundetail" },
      h("thead", {}, h("tr", {}, h("th", {}, "result"), h("th", {}, "kind"),
        h("th", {}, "check"), h("th", {}, "desired"), h("th", {}, "output"))),
      h("tbody", {}, (checks || []).map(checkRow)));
  }

  function teaser(code) {
    var line = (code || "").split("\n").find(function (l) { return l.trim(); }) || "";
    return line.length > 90 ? line.slice(0, 90) + "…" : line;
  }

  function resourceCard(s, svc) {
    var ok = s.ok !== false;
    var summary = h("summary", {},
      h("span", { class: "n" }, "step " + s.step),
      h("span", { class: "teaser" }, "📄 read_skill_file  " + s.path),
      ok ? null : h("span", { class: "badge fail" }, "not found"));
    var body;
    if (ok) {
      var note = s.content_truncated ? " [+" + (s.content_len - (s.content || "").length) + " chars truncated]" : "";
      body = [h("a", { class: "chip", href: hSkills(svc, s.path) }, "open in skills explorer →"),
        h("pre", { class: "resource" }, s.content || "(empty file)"),
        note ? h("div", { class: "trunc" }, note) : null];
    } else {
      body = [h("pre", { class: "error" }, s.error || "error")];
    }
    return h("details", { class: "step resource" + (ok ? "" : " err"), open: (ui.expand || !ok) ? "" : null },
      summary, body);
  }

  function stepCard(s, svc) {
    if (s.kind === "skill_file") return resourceCard(s, svc);
    var hasErr = !!s.error;
    var summary = h("summary", {},
      h("span", { class: "n" }, "step " + s.step),
      h("span", { class: "teaser" }, teaser(s.code)),
      hasErr ? h("span", { class: "badge fail" }, "error") : null);
    var outs = [];
    if (s.stdout) {
      var note = s.stdout_truncated ? " [+" + (s.stdout_len - s.stdout.length) + " chars truncated]" : "";
      outs.push(h("details", { class: "out", open: s.stdout.length < 1200 ? "" : null },
        h("summary", {}, "stdout" + (note ? "" : "")),
        h("pre", {}, s.stdout), note ? h("div", { class: "trunc" }, note) : null));
    }
    if (s.stderr) outs.push(h("div", { class: "out" }, h("pre", { class: "stderr" }, s.stderr)));
    if (s.error) outs.push(h("div", { class: "out" }, h("pre", { class: "error" }, s.error)));
    var code = h("pre", { class: "codeblock" }, h("code", { class: "language-python" }, s.code || ""));
    return h("details", { class: "step" + (hasErr ? " err" : ""), open: (ui.expand || hasErr) ? "" : null },
      summary, code, outs);
  }

  function runDetail(run) {
    var group = groups[run.ref + "|" + run.model] || [run];
    var reps = h("div", { class: "reptabs" }, group.map(function (r) {
      return h("button", { class: r.run_uid === run.run_uid ? "active" : "",
        onClick: function () { location.hash = hResults(r.run_uid); } },
        h("span", { class: "badge " + (r.passed ? "pass" : "fail") }, r.passed ? "✓" : "✗"), "rep " + r.rep);
    }));

    var docChips = (run.docs_opened || []).map(function (p) {
      return h("a", { class: "chip", href: hSkills(run.service, p) }, p);
    });
    docChips.unshift(h("a", { class: "chip", href: hSkills(run.service, "SKILL.md") }, h("b", {}, "SKILL.md"), " (always loaded)"));

    var verdict = h("div", { class: "verdict" },
      h("span", { class: "badge " + (run.passed ? "pass" : "fail") }, run.passed ? "PASS" : "FAIL"),
      h("span", { class: "muted" }, "score " + (run.score != null ? run.score : "?")),
      h("span", { class: "muted" }, run.steps + " steps"),
      h("span", { class: "muted" }, (run.elapsed_s != null ? run.elapsed_s + "s" : "")),
      run.error ? h("span", { class: "err" }, "error: " + run.error) : null);

    var steps = run.trace || [];
    var trace = steps.map(function (s) { return stepCard(s, run.service); });
    var nLoads = steps.filter(function (s) { return s.kind === "skill_file"; }).length;

    return h("div", { class: "panel" },
      h("a", { class: "readonly", href: hSkills(run.service, "SKILL.md") }, "View full skill →"),
      h("h2", {}, run.title || run.leaf),
      h("div", { class: "sub" }, run.ref + "  ·  " + run.model + "  ·  rep " + run.rep),
      reps, verdict,
      h("div", { class: "section-h" }, "Checks"),
      checksTable(run.checks),
      h("div", { class: "section-h" }, "What the agent was shown"),
      h("div", { class: "docchips" }, docChips),
      h("div", { class: "section-h" }, "Final answer"),
      h("details", { class: "out", open: "" }, h("summary", {}, "answer"), h("pre", {}, run.final_answer || "(none)")),
      h("div", { class: "section-h" }, "Trace · " + steps.length + " steps"
        + (nLoads ? " · " + nLoads + " skill load" + (nLoads === 1 ? "" : "s") : "")),
      trace.length ? trace : h("div", { class: "muted" }, "(no steps)"));
  }

  // -- SKILLS view --------------------------------------------------------
  function skillsView(sel) {
    var svcs = Object.keys(skillByService);
    if (!svcs.length) return h("div", { class: "empty" }, "No skills captured in this report.");
    var svc = sel.svc && skillByService[sel.svc] ? sel.svc : svcs[0];
    var skill = skillByService[svc];
    var path = sel.path && skill.rendered[sel.path] ? sel.path : "SKILL.md";

    var picker = h("div", { class: "svcpick" }, svcs.map(function (s) {
      return h("button", { class: s === svc ? "active" : "", onClick: function () { location.hash = hSkills(s, "SKILL.md"); } },
        skillByService[s].name || s);
    }));

    var byGroup = { "": [] };
    skill.files.forEach(function (f) {
      if (f.path === "SKILL.md") { byGroup[""].push(f); return; }
      var top = f.path.indexOf("/") >= 0 ? f.path.split("/")[0] : "other";
      (byGroup[top] = byGroup[top] || []).push(f);
    });
    var treeKids = [];
    function fileLink(f) {
      var hasReach = f.reach && f.reach.total > 0 && f.path !== "SKILL.md";
      var cold = hasReach && f.reach.opened === 0;
      return h("a", { class: "file" + (f.path === path ? " active" : "") + (f.path === "SKILL.md" ? " pinned" : "") + (cold ? " cold" : ""),
        href: hSkills(svc, f.path) },
        h("span", {}, f.path.split("/").pop()),
        hasReach ? h("span", { class: "reach", title: "opened in runs" }, f.reach.opened + "/" + f.reach.total) : null);
    }
    byGroup[""].forEach(function (f) { treeKids.push(fileLink(f)); });
    ["references", "examples", "assets", "other"].forEach(function (grp) {
      if (!byGroup[grp]) return;
      treeKids.push(h("div", { class: "grp" }, grp));
      byGroup[grp].forEach(function (f) { treeKids.push(fileLink(f)); });
    });
    Object.keys(byGroup).forEach(function (grp) {
      if (grp === "" || ["references", "examples", "assets", "other"].indexOf(grp) >= 0) return;
      treeKids.push(h("div", { class: "grp" }, grp));
      byGroup[grp].forEach(function (f) { treeKids.push(fileLink(f)); });
    });

    var tree = h("div", { class: "tree" }, picker, treeKids);
    var doc = h("div", { class: "doc" },
      h("span", { class: "readonly" }, "read-only" + (skill.skill_sha ? " · @" + skill.skill_sha : "")),
      h("div", { html: skill.rendered[path] || "" }));
    return h("div", { class: "split" }, tree, doc);
  }

  // -- TESTS view ---------------------------------------------------------
  function testsView(sel) {
    if (!DATA.tests.length) return h("div", { class: "empty" }, "No tests in corpus.");
    var ref = sel.ref && testByRef[sel.ref] ? sel.ref : DATA.tests[0].ref;
    var t = testByRef[ref];

    var svcOrder = {}; (DATA.services || []).forEach(function (s, i) { svcOrder[s] = i; });
    var sorted = DATA.tests.slice().sort(function (a, b) {
      return ((svcOrder[a.service] == null ? 99 : svcOrder[a.service]) - (svcOrder[b.service] == null ? 99 : svcOrder[b.service])) ||
        a.service.localeCompare(b.service) || a.category.localeCompare(b.category) || a.leaf.localeCompare(b.leaf);
    });
    function skillLabel(svc) { var s = skillByService[svc]; return (s && s.name) ? s.name : svc.toUpperCase(); }

    // group the whole corpus into a skill > category > test tree (collapsible)
    var bySvc = {}, svcSeq = [];
    sorted.forEach(function (x) {
      if (!bySvc[x.service]) { bySvc[x.service] = { cats: {}, seq: [], n: 0 }; svcSeq.push(x.service); }
      var b = bySvc[x.service];
      if (!b.cats[x.category]) { b.cats[x.category] = []; b.seq.push(x.category); }
      b.cats[x.category].push(x); b.n++;
    });
    var listKids = svcSeq.map(function (svc) {
      var b = bySvc[svc];
      var svcActive = b.seq.some(function (cat) { return b.cats[cat].some(function (x) { return x.ref === ref; }); });
      var catEls = b.seq.map(function (cat) {
        var tests = b.cats[cat];
        var catActive = tests.some(function (x) { return x.ref === ref; });
        return h("details", { class: "treegrp cat", open: catActive ? "" : null },
          h("summary", {}, h("span", { class: "nm" }, cat), h("span", { class: "count" }, String(tests.length))),
          tests.map(function (x) {
            return h("a", { class: x.ref === ref ? "active" : "", href: hTests(x.ref) }, x.leaf);
          }));
      });
      return h("details", { class: "treegrp skill", open: svcActive ? "" : null },
        h("summary", {},
          h("span", { class: "nm" }, skillLabel(svc)),
          h("span", { class: "code" }, svc),
          h("span", { class: "count" }, String(b.n))),
        catEls);
    });
    function setAllOpen(open) {
      document.querySelectorAll(".testlist details.treegrp").forEach(function (d) {
        if (open) d.setAttribute("open", ""); else d.removeAttribute("open");
      });
    }
    var treetools = h("div", { class: "treetools" },
      h("button", { onClick: function () { setAllOpen(true); } }, "expand all"),
      h("button", { onClick: function () { setAllOpen(false); } }, "collapse all"));
    var list = h("div", { class: "tree testlist" }, treetools, listKids);

    var checks = h("table", { class: "checks answerkey" }, h("tbody", {}, t.checks.map(function (c) {
      return h("tr", {},
        h("td", { class: "fam" }, h("span", { class: "chip-fam " + c.family }, c.family)),
        h("td", {}, h("span", { class: "checktype" }, c.type),
          h("span", { class: "spec" }, c.spec || "")));
    })));
    var refRuns = DATA.runs.filter(function (r) { return r.ref === ref; });
    var runsBlock = refRuns.length ? h("div", { class: "docchips" }, refRuns.map(function (r) {
      return h("a", { class: "chip", href: hResults(r.run_uid) },
        h("span", { class: "badge " + (r.passed ? "pass" : "fail") }, r.passed ? "✓" : "✗"),
        " " + r.model.split("/").pop() + " rep " + r.rep);
    })) : h("div", { class: "muted" }, "no runs for this test in the loaded report(s)");

    var doc = h("div", { class: "doc" },
      h("span", { class: "readonly" }, "read-only"),
      h("h2", {}, t.title), h("div", { class: "sub" }, t.ref),
      h("div", { class: "section-h" }, "Prompt (shown to the agent)"),
      h("div", { class: "test-prompt", html: t.prompt_html }),
      t.rationale_html ? h("div", { class: "section-h" }, "Rationale (not shown to the agent)") : null,
      t.rationale_html ? h("div", { html: t.rationale_html }) : null,
      h("div", { class: "section-h" }, "Checks (eval.yaml)"), checks,
      h("details", { class: "out" }, h("summary", {}, "raw eval.yaml"), h("pre", {}, t.eval_yaml)),
      h("div", { class: "section-h" }, "Runs"), runsBlock);
    return h("div", { class: "split" }, list, doc);
  }

  // -- render -------------------------------------------------------------
  function render() {
    var sel = route();
    APP.textContent = "";
    APP.append(header(), tabs(sel.view));
    if (sel.view === "skills") APP.append(skillsView(sel));
    else if (sel.view === "tests") APP.append(testsView(sel));
    else APP.append(resultsView(sel));
    if (sel.uid) { var d = APP.querySelector(".panel"); if (d) d.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  }

  render();
})();
