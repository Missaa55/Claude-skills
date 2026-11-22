"use strict";
const $ = selector => document.querySelector(selector);
const state = { user: null, csrf: "", customers: [], jobs: [], selected: null, customer: null };
const labels = { planned: "Naplánováno", in_progress: "V realizaci", completed: "Dokončeno", cancelled: "Zrušeno" };
const money = cents => new Intl.NumberFormat("cs-CZ", { style: "currency", currency: "CZK" }).format(cents / 100);
function cents(value) { if (!/^\d+([,.]\d{1,2})?$/.test(value)) throw new Error("Zadejte cenu s nejvýše dvěma desetinnými místy."); const [whole, decimal = ""] = value.replace(",", ".").split("."); const result = Number(whole) * 100 + Number(decimal.padEnd(2, "0")); if (!Number.isSafeInteger(result) || result > 100000000) throw new Error("Cena je příliš vysoká."); return result; }
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
function notice(message, error = false) { $("#notice").textContent = message; $("#notice").classList.toggle("error", error); }
async function api(path, method = "GET", body) {
  const response = await fetch(`/api/${path}`, { method, headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrf }, ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal: AbortSignal.timeout(10000) });
  const data = await response.json();
  if (!response.ok) { if (response.status === 401 && path !== "login") showLogin(); throw new Error(data.error || "Požadavek se nezdařil."); }
  return data;
}
function showLogin() { state.user = null; state.csrf = ""; $("#application").hidden = true; $("#login-view").hidden = false; }
function action(text, callback, danger = false) { const button = node("button", text, danger ? "danger" : "quiet"); button.type = "button"; button.addEventListener("click", () => Promise.resolve().then(callback).catch(error => notice(error.message, true))); return button; }
async function refresh() {
  [state.customers, state.jobs] = await Promise.all([api("customers"), api("jobs")]);
  $("#count").textContent = state.jobs.length; $("#active-count").textContent = state.jobs.filter(job => job.status === "in_progress").length;
  $("#total").textContent = money(state.jobs.reduce((sum, job) => sum + job.total_cents, 0));
  const select = $("#job-form select"); select.replaceChildren();
  select.append(new Option(state.customers.length ? "Vyberte zákazníka" : "Nejprve přidejte zákazníka", ""));
  state.customers.forEach(customer => select.append(new Option(customer.name, customer.id)));
  const jobs = $("#job-list"); jobs.replaceChildren();
  if (!state.jobs.length) jobs.append(node("p", "Zatím tu nejsou žádné zakázky. Přidejte zákazníka a založte první práci.", "empty"));
  state.jobs.forEach(job => {
    const row = node("div", undefined, "job-row"); const title = node("div", undefined, "row-title"); title.append(node("strong", job.title), node("small", state.customers.find(customer => customer.id === job.customer_id)?.name || "Přiřazený zákazník"));
    const actions = node("div", undefined, "row-actions"); actions.append(action("Otevřít detail", () => openJob(job.id)));
    row.append(title, node("span", labels[job.status], `badge ${job.status}`), node("span", money(job.total_cents), "row-price"), actions); jobs.append(row);
  });
  const customers = $("#customer-list"); customers.replaceChildren();
  if (!state.customers.length) customers.append(node("p", "Adresář je prázdný. Uložte první syntetický kontakt.", "empty"));
  state.customers.forEach(customer => {
    const row = node("div", undefined, "customer-row"); const title = node("div", undefined, "row-title"); title.append(node("strong", customer.name), node("small", `${customer.email}${customer.phone ? ` · ${customer.phone}` : ""}`)); row.append(title);
    if (state.user.role !== "viewer") { const actions = node("div", undefined, "row-actions"); actions.append(action("Upravit", () => editCustomer(customer)), action("Smazat", async () => { if (confirm(`Smazat zákazníka ${customer.name}? Zákazníka s navázanou zakázkou nelze odstranit.`)) { await api(`customers/${customer.id}`, "DELETE"); await refresh(); notice("Zákazník byl odstraněn."); } }, true)); row.append(actions); }
    customers.append(row);
  });
  if (state.selected) { const current = state.jobs.find(job => job.id === state.selected.id); if (current) renderDetail(current); else { state.selected = null; $("#job-detail").hidden = true; } }
}
function renderDetail(job) {
  state.selected = job; $("#job-detail").hidden = false; $("#detail-title").textContent = job.title;
  const form = $("#edit-job-form"); form.elements.title.value = job.title; form.elements.status.value = job.status; form.elements.labor.value = (job.labor_cents / 100).toFixed(2);
  const list = $("#material-list"); list.replaceChildren();
  if (!job.materials.length) list.append(node("li", "Bez materiálových položek."));
  job.materials.forEach(material => { const li = node("li"); li.append(node("span", `${material.name} · ${material.quantity} × ${money(material.unit_price_cents)}`), node("strong", money(material.quantity * material.unit_price_cents))); if (state.user.role !== "viewer") li.append(action("Odebrat", async () => { if (confirm(`Odebrat položku ${material.name}?`)) { await api(`materials/${material.id}`, "DELETE"); await refresh(); } }, true)); list.append(li); });
  $("#detail-total").textContent = `Celkem ${money(job.total_cents)} · práce ${money(job.labor_cents)}`;
}
async function openJob(id) { renderDetail(await api(`jobs/${id}`)); $("#job-detail").scrollIntoView({ block: "start" }); }
function editCustomer(customer) { state.customer = customer; const form = $("#customer-form"); for (const key of ["name", "email", "phone"]) form.elements[key].value = customer[key]; $("#customer-form-title").textContent = "Upravit zákazníka"; $("#cancel-customer").hidden = false; form.elements.name.focus(); }
function resetCustomer() { state.customer = null; $("#customer-form").reset(); $("#customer-form-title").textContent = "Nový zákazník"; $("#cancel-customer").hidden = true; }
function submit(selector, callback) { $(selector).addEventListener("submit", async event => { event.preventDefault(); const form = event.currentTarget; if (!form.reportValidity()) return; const button = form.querySelector("button[type=submit],button:not([type])"); button.disabled = true; try { await callback(form); } catch (error) { if (selector === "#login-form") $("#login-error").textContent = error.message; else notice(error.message, true); } finally { button.disabled = false; } }); }
async function enter(user) { state.user = user; state.csrf = user.csrf_token; $("#identity").textContent = `${user.username} · ${user.role}`; $("#login-view").hidden = true; $("#application").hidden = false; for (const selector of ["#job-form", "#customer-form", "#edit-job-form", "#material-form", "#delete-job"]) $(selector).hidden = user.role === "viewer"; await refresh(); }
submit("#login-form", async form => { $("#login-error").textContent = ""; await enter(await api("login", "POST", Object.fromEntries(new FormData(form)))); form.reset(); });
submit("#customer-form", async form => { await api(state.customer ? `customers/${state.customer.id}` : "customers", state.customer ? "PATCH" : "POST", Object.fromEntries(new FormData(form))); resetCustomer(); await refresh(); notice("Zákazník je uložený."); });
submit("#job-form", async form => { const data = Object.fromEntries(new FormData(form)); const job = await api("jobs", "POST", { title: data.title, customer_id: Number(data.customer_id), labor_cents: cents(data.labor) }); form.reset(); await refresh(); await openJob(job.id); notice("Zakázka je vytvořená."); });
submit("#edit-job-form", async form => { const data = Object.fromEntries(new FormData(form)); await api(`jobs/${state.selected.id}`, "PATCH", { title: data.title, status: data.status, customer_id: state.selected.customer_id, labor_cents: cents(data.labor) }); await refresh(); notice("Změny jsou uložené."); });
submit("#material-form", async form => { const data = Object.fromEntries(new FormData(form)); await api(`jobs/${state.selected.id}/materials`, "POST", { name: data.name, quantity: Number(data.quantity), unit_price_cents: cents(data.price) }); form.reset(); await refresh(); notice("Materiál je přidaný."); });
$("#cancel-customer").addEventListener("click", resetCustomer);
$("#close-detail").addEventListener("click", () => { $("#job-detail").hidden = true; state.selected = null; });
$("#delete-job").addEventListener("click", async () => { if (!state.selected || !confirm(`Smazat zakázku ${state.selected.title} včetně materiálů?`)) return; try { await api(`jobs/${state.selected.id}`, "DELETE"); state.selected = null; $("#job-detail").hidden = true; await refresh(); notice("Zakázka byla odstraněna."); } catch (error) { notice(error.message, true); } });
$("#logout").addEventListener("click", async () => { try { await api("logout", "POST", {}); state.selected = null; showLogin(); } catch (error) { notice(error.message, true); } });
api("me").then(enter).catch(() => showLogin());
