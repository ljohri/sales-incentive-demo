function formatMoney(n) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

function formatPct(n) {
  return `${n.toFixed(2)}%`;
}

const form = document.getElementById("estimate-form");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const tierRows = document.getElementById("tier-rows");
const tieredTotalEl = document.getElementById("tiered-total");
const unitBonusEl = document.getElementById("unit-bonus");
const totalPayoutEl = document.getElementById("total-payout");
const explanationEl = document.getElementById("explanation");

async function runEstimate(salesAmount, unitsSold) {
  const res = await fetch("/estimate/monthly", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sales_amount: salesAmount,
      units_sold: unitsSold,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || (Array.isArray(data.detail) ? data.detail[0]?.msg : null) || res.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

function renderResults(data) {
  tierRows.innerHTML = "";
  for (const line of data.tier_lines) {
    if (line.amount_in_bracket <= 0) continue;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${line.bracket_label}</td>
      <td>${formatMoney(line.amount_in_bracket)}</td>
      <td>${formatPct(line.rate_pct)}</td>
      <td>${formatMoney(line.commission)}</td>
    `;
    tierRows.appendChild(tr);
  }
  tieredTotalEl.textContent = formatMoney(data.tiered_commission);
  unitBonusEl.textContent = formatMoney(data.unit_bonus);
  totalPayoutEl.textContent = formatMoney(data.total_payout);
  explanationEl.innerHTML = "";
  for (const line of data.explanation) {
    const li = document.createElement("li");
    li.textContent = line;
    explanationEl.appendChild(li);
  }
  resultsEl.hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.hidden = true;
  const btn = form.querySelector("button[type=submit]");
  btn.disabled = true;
  try {
    const sales = parseFloat(document.getElementById("sales_amount").value);
    const units = parseInt(document.getElementById("units_sold").value, 10);
    if (Number.isNaN(sales) || sales < 0) throw new Error("Enter a valid sales amount.");
    if (Number.isNaN(units) || units < 0) throw new Error("Enter a valid unit count.");
    const data = await runEstimate(sales, units);
    renderResults(data);
  } catch (err) {
    errorEl.textContent = err.message || "Calculation failed.";
    errorEl.hidden = false;
    resultsEl.hidden = true;
  } finally {
    btn.disabled = false;
  }
});

// Initial calculation on load
form.dispatchEvent(new Event("submit"));
