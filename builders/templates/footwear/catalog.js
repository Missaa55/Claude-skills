"use strict";
const selections = [];
document.querySelectorAll("[data-cart]").forEach(button => button.addEventListener("click", () => {
  const size = button.closest("article").querySelector("select").value;
  const model = button.dataset.cart;
  selections.push({model, size});
  document.querySelector("#selection-status").textContent = `Ukázkový výběr: ${selections.map(item => `${item.model}, velikost ${item.size}`).join("; ")}. Nejde o skutečnou objednávku.`;
}));
