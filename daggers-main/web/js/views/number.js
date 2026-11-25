/* Daggers · Number check — before you answer or call back (plan Scenario 8).
   Server-side offline rules (POST /api/number); nothing is stored. Never shows SAFE. */
import { t } from "../i18n/i18n.js";
import { checkNumber, getExamples } from "../api.js";
import { el, tagChip } from "../components/tag.js";
import { emptyState } from "../components/empty.js";
import { pageHead, card } from "./_shared.js";
import { icons } from "../components/icons.js";

export default async function NumberView() {
  const root = el("div");
  root.append(pageHead({
    kicker: t("number.kicker"), title: t("number.title"), subtitle: t("number.subtitle"),
    actions: [el("a", { class: "btn btn-sm", href: "#/check" }, el("span", { html: icons.check({ size: 16 }) }), document.createTextNode(t("number.toChecker")))],
  }));
  const wrap = el("div", { class: "stack" });
  root.append(wrap);

  const input = el("input", {
    class: "input mono ltr", dir: "ltr", type: "tel", inputmode: "tel", maxlength: "40",
    placeholder: t("number.placeholder"), "aria-label": t("number.inputLabel"), autocomplete: "off",
  });
  input.id = "numberInput";
  const btn = el("button", { class: "btn btn-primary btn-lg", type: "submit" },
    el("span", { html: icons.phone({ size: 18 }) }), el("span", { text: t("number.btn") }));
  const form = el("form", { class: "stack", style: "gap:var(--s3)" });
  form.append(el("div", { class: "field" },
    el("label", { for: "numberInput", text: t("number.inputLabel") }),
    el("div", { class: "input-row" }, input, btn)));

  // Example numbers only if the backend provides them (it ships none: no sample data).
  const exRow = el("div", { class: "pill-row", style: "display:none" },
    el("span", { class: "muted", style: "font-size:var(--fs-xs); align-self:center", text: t("number.examplesTitle") }));
  getExamples().then((ex) => {
    const list = Array.isArray(ex?.numbers) ? ex.numbers : [];
    list.forEach((n) => {
      const b = el("button", { type: "button", class: "query-pill mono ltr", text: n });
      b.addEventListener("click", () => { input.value = n; input.focus(); });
      exRow.append(b);
    });
    exRow.style.display = list.length ? "" : "none";
  }).catch(() => { exRow.style.display = "none"; });
  form.append(exRow);

  const resultHost = el("div");
  resultHost.append(emptyState({ title: t("number.emptyTitle"), body: t("number.sourceNote"), mood: "calm" }));
  const honest = card(t("number.honestTitle"), "", el("p", { style: "font-size:var(--fs-sm)", text: t("number.honestBody") }));
  wrap.append(card(null, "", form), el("div", { class: "grid-2", style: "align-items:start" }, resultHost, honest));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const v = input.value.trim();
    if (!v) { input.focus(); return; }
    btn.disabled = true;
    resultHost.replaceChildren(el("p", { class: "muted", text: t("number.checking") }));
    try {
      resultHost.replaceChildren(numberCard(await checkNumber(v)));
    } catch (err) {
      const key = err?.status === 422 ? "number.invalid" : err?.status === 429 ? "number.rateLimited" : "number.error";
      resultHost.replaceChildren(el("div", { class: "note" }, el("span", { text: "!" }), el("span", { text: t(key) })));
    } finally {
      btn.disabled = false;
    }
  });

  return root;
}

function numberCard(res) {
  const tag = String(res.tag || "WARNING").toLowerCase();       // never "safe" for a number
  const titleKey = tag === "fake" ? "number.fakeTitle" : res.warning_signs ? "number.warnTitle" : "number.cleanTitle";
  const c = el("section", { class: "card" });
  c.append(el("div", { class: "row", style: "justify-content:space-between" },
    tagChip(tag, { size: "lg" }),
    el("span", { class: "mono ltr", style: "font-weight:600", text: Number(res.score ?? 0).toFixed(2) })));
  c.append(el("div", { class: "vh-domain mono ltr", dir: "ltr", text: res.number || res.input }));
  c.append(el("div", { style: "font-weight:600; margin-block-start:var(--s2)", text: t(titleKey) }));
  if (!res.warning_signs) c.append(el("p", { class: "muted", style: "font-size:var(--fs-sm)", text: t("number.cleanBody") }));
  const signs = Array.isArray(res.signs) ? res.signs : [];
  if (signs.length) {
    // translated rule family + the engine's exact detail (e.g. which premium range)
    c.append(el("ul", { style: "margin:var(--s3) 0 0; padding-inline-start:var(--s4); font-size:var(--fs-sm)" },
      ...signs.map((s) => el("li", {},
        el("span", { text: t(`number.sign_${s.code}`) }),
        el("span", { class: "muted ltr", dir: "ltr", style: "font-size:var(--fs-xs); display:block", text: String(s.detail || "") })))));
  }
  if (tag !== "warning" || res.warning_signs) {
    c.append(el("p", { style: "font-size:var(--fs-sm); margin-block-start:var(--s3)", text: t("number.advice") }));
  }
  c.append(el("p", { class: "muted", style: "font-size:var(--fs-xs); margin-block-start:var(--s3)", text: t("number.sourceNote") }));
  return c;
}
