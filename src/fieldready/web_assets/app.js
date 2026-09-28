"use strict";
const $ = id => document.getElementById(id);
let token = sessionStorage.getItem("fieldready-token") || "";
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has("token")) {
  token = fragment.get("token");
  sessionStorage.setItem("fieldready-token", token);
  history.replaceState(null, "", location.pathname);
}

let run = "", offset = 0, nextOffset = null, selected = null, hasModel = false, busy = false;

function message(text, error = false) {
  $("message").textContent = text;
  $("message").className = error ? "error" : "";
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    redirect: "error"
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Local request failed.");
  return data;
}

async function perform(task) {
  if (busy) return;
  busy = true;
  try { await task(); }
  catch (error) { message(error.message, true); }
  finally { busy = false; }
}

function clearSelection() {
  selected = null;
  $("selection").textContent = "Select a finding to inspect its evidence.";
  $("evidence").replaceChildren();
  $("review-controls").disabled = true;
  $("confirm").checked = false;
  $("reason").value = "";
  $("ask").disabled = true;
  $("answer").textContent = "";
}

function selectFinding(item) {
  if (busy) return;
  clearSelection();
  selected = item;
  $("selection").textContent = "Record ordinal " + item.row_number + " · revision " + item.revision;
  const labels = {
    record_id:"Record ID",
    rule_id:"Rule",
    category:"Category",
    severity:"Severity",
    field:"Field",
    observed:"Observed",
    expected:"Expected",
    status:"Status",
    message:"Why flagged",
    verification:"What to verify"
  };
  for (const [key, label] of Object.entries(labels)) {
    if (!(key in item)) continue;
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = String(item[key] ?? "") || "(missing)";
    $("evidence").append(dt, dd);
  }
  $("review-controls").disabled = false;
  $("ask").disabled = !hasModel;
  document.querySelectorAll("#rows tr").forEach(
    row => row.classList.toggle("selected", row.dataset.id === item.finding_id)
  );
}

async function info() {
  const data = await api("/api/info");

  const currentRuleset = $("import-ruleset").value;
  $("import-ruleset").replaceChildren();
  for (const item of data.rulesets) {
    const label = item.title + " · " + item.id;
    $("import-ruleset").add(new Option(label, item.id));
  }
  if ([...$("import-ruleset").options].some(option => option.value === currentRuleset)) {
    $("import-ruleset").value = currentRuleset;
  }

  $("runs").replaceChildren(new Option("Choose a review", ""));
  for (const item of data.runs) {
    const stamp = item.created_at.slice(0,19).replace("T"," ");
    $("runs").add(new Option(stamp + " UTC · " + item.ruleset_id + " · " + item.id.slice(0,8), item.id));
  }
  $("runs").value = run;

  hasModel = !!data.model;
  $("model-status").textContent = hasModel
    ? "Configured local model: " + data.model + ". Scope remains deterministic; AI focus is advisory."
    : "AI disabled. Validation, review and export remain available.";
}

async function load() {
  clearSelection();
  $("export").disabled = !run;

  if (!run) {
    for (const id of ["records","findings","affected","unresolved"]) $(id).textContent = "—";
    $("rows").replaceChildren();
    $("page-label").textContent = "No review selected";
    $("coverage").textContent = "Create a synthetic review or reopen a saved run.";
    nextOffset = null;
    $("previous").disabled = true;
    $("next").disabled = true;
    return;
  }

  const data = await api("/api/run", {
    run_id: run,
    status: $("filter").value || null,
    offset
  });
  const s = data.summary, page = data.page;

  for (const [id,key] of Object.entries({
    records:"row_count", findings:"finding_count", affected:"affected_rows", unresolved:"unresolved_findings"
  })) $(id).textContent = s[key];

  const checks = s.check_evaluations || {
    evaluable: s.total_checks_evaluable || 0,
    not_evaluable: (s.total_checks_not_evaluable || []).length
  };
  const severity = s.severity_counts || {};
  const severityText = ["critical","high","medium","low"]
    .filter(key => severity[key])
    .map(key => key + " " + severity[key])
    .join(", ") || "none";

  $("coverage").textContent =
    "Ruleset: " + (s.ruleset_title || s.ruleset) +
    " · version " + (s.ruleset_version || "—") +
    " · rule evaluations: " + checks.evaluable + " evaluable / " + checks.not_evaluable + " not evaluable" +
    " · severity: " + severityText +
    " · run: " + run;

  $("rows").replaceChildren();
  for (const item of page.items) {
    const tr = document.createElement("tr");
    tr.dataset.id = item.finding_id;
    for (const key of ["row_number","record_id","rule_id","severity","status"]) {
      const td = document.createElement("td");
      td.textContent = String(item[key] ?? "") || "(missing)";
      tr.append(td);
    }
    const td = document.createElement("td");
    const button = document.createElement("button");
    button.textContent = "Review";
    button.className = "secondary";
    button.addEventListener("click", () => selectFinding(item));
    td.append(button);
    tr.append(td);
    $("rows").append(tr);
  }

  nextOffset = page.next_offset;
  $("previous").disabled = offset === 0;
  $("next").disabled = nextOffset === null;
  $("page-label").textContent = page.total_matching
    ? (offset + 1) + "–" + (offset + page.items.length) + " of " + page.total_matching + " findings"
    : "No findings match this filter";
  message("Review loaded through MCP. Counts reflect stored evidence; source records are unchanged.");
}

async function startDemo(path) {
  const data = await api(path, {request_id: crypto.randomUUID()});
  run = data.run_id;
  offset = 0;
  $("filter").value = "";
  await info();
  await load();
}

$("demo").onclick = () => perform(async () => startDemo("/api/demo"));
$("demo-field").onclick = () => perform(async () => startDemo("/api/demo-field"));

$("csv").onchange = () => perform(async () => {
  const file = $("csv").files[0];
  if (!file) return;
  if (file.size > 1048576) throw new Error("CSV must not exceed 1 MiB.");
  const data = await api("/api/import", {
    csv: await file.text(),
    ruleset_id: $("import-ruleset").value,
    request_id: crypto.randomUUID()
  });
  run = data.run_id;
  offset = 0;
  $("filter").value = "";
  await info();
  await load();
  $("csv").value = "";
});

$("runs").onchange = () => perform(async () => {
  run = $("runs").value;
  offset = 0;
  await load();
});

$("refresh").onclick = () => perform(async () => {
  await info();
  await load();
});

$("export").onclick = () => perform(async () => {
  if (!run) throw new Error("Select a review before exporting.");
  const result = await api("/api/export", {run_id: run});
  message("Review package exported locally: " + result.output_dir + ". Raw source CSV was not included.");
});

$("filter").onchange = () => perform(async () => {
  offset = 0;
  await load();
});

$("previous").onclick = () => perform(async () => {
  offset = Math.max(0, offset - 50);
  await load();
});

$("next").onclick = () => perform(async () => {
  if (nextOffset !== null) {
    offset = nextOffset;
    await load();
  }
});

$("status").onchange = $("reason").oninput = () => {
  $("confirm").checked = false;
};

$("review-form").onsubmit = event => {
  event.preventDefault();
  perform(async () => {
    if (!selected || !$("confirm").checked) {
      throw new Error("Select a finding and explicitly confirm the decision.");
    }
    const body = {
      finding_id: selected.finding_id,
      status: $("status").value,
      reason: $("reason").value,
      expected_revision: selected.revision,
      request_id: crypto.randomUUID(),
      confirmed: true
    };
    await api("/api/decision", body);
    await load();
    message("Decision saved. The original CSV was not changed.");
  });
};

$("ask-form").onsubmit = event => {
  event.preventDefault();
  perform(async () => {
    if (!selected || !hasModel) {
      throw new Error("Select a finding and enable an installed local model first.");
    }
    const id = selected.finding_id;
    $("ask").disabled = true;
    $("answer").textContent = "Running local inference… No review decision will be saved.";
    try {
      const result = await api("/api/explain", {
        run_id: run,
        finding_id: id,
        question: $("question").value
      });
      const focus = result.focus ? " · Focus: " + result.focus : "";
      $("answer").textContent =
        result.text + "\n\n" + result.notice +
        "\nModel: " + result.model + focus +
        " · " + result.elapsed_seconds + " s" +
        " · Evidence: " + result.finding_id + " / " + result.rule_id;
      message(result.routing_source === "deterministic_scope_guard"
        ? "The deterministic scope guard rejected an unrelated question before model inference."
        : "Scope was accepted deterministically; local AI classified the review focus and Python rendered the evidence-grounded explanation.");
    } catch (error) {
      $("answer").textContent = "No explanation produced. " + error.message;
      throw error;
    } finally {
      $("ask").disabled = !hasModel || !selected;
    }
  });
};

perform(async () => {
  await info();
  message("Local workspace ready. Start the richer field-survey demo or reopen a saved review.");
});
