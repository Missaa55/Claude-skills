"use strict";
const toggle = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#navigation");
function closeMenu() { navigation.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); }
toggle.addEventListener("click", () => { const open = toggle.getAttribute("aria-expanded") !== "true"; navigation.classList.toggle("open", open); toggle.setAttribute("aria-expanded", String(open)); });
navigation.addEventListener("click", event => { if (event.target.closest("a")) closeMenu(); });
document.addEventListener("keydown", event => { if (event.key === "Escape" && navigation.classList.contains("open")) { closeMenu(); toggle.focus(); } });
const form = document.querySelector("#enquiry");
const status = document.querySelector("#form-status");
form.addEventListener("submit", async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const button = form.querySelector("button");
  button.disabled = true;
  status.textContent = "Ukládám testovací poptávku…";
  status.dataset.error = "false";
  try {
    const data = Object.fromEntries(new FormData(form));
    data.consent = form.elements.consent.checked;
    const response = await fetch("/api/enquiries", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data), signal: AbortSignal.timeout(10000) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Poptávku se nepodařilo uložit.");
    status.textContent = `Testovací poptávka č. ${result.id} je uložená. Děkujeme za vyzkoušení.`;
    form.reset();
  } catch (error) {
    status.dataset.error = "true";
    status.textContent = error.name === "TypeError" || error.name === "TimeoutError" ? "Spojení se nezdařilo. Zkuste poptávku odeslat znovu." : error.message;
  } finally { button.disabled = false; }
});
