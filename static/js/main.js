/* Live quote on the booking page. Prices and availability come from the server (same logic as the real booking). */
(function () {
  var form = document.getElementById("booking-form");
  if (!form) return;
  var box = document.getElementById("quote-result");
  var url = form.dataset.quoteUrl;
  var money = form.dataset.currency || "$";
  var msg = JSON.parse(document.getElementById("quote-i18n").textContent);
  var timer = null;

  function fmt(n) { return money + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  function refresh() {
    var rt = form.querySelector("[name=room_type]").value;
    var ci = form.querySelector("[name=check_in]").value;
    var co = form.querySelector("[name=check_out]").value;
    var coInput = form.querySelector("[name=check_out]");
    if (ci) {
      var d = new Date(ci); d.setDate(d.getDate() + 1);
      coInput.min = d.toISOString().slice(0, 10);
    }
    if (!rt || !ci || !co) { box.innerHTML = "<p class='mb-0'>" + msg.select + "</p>"; return; }
    fetch(url + "?room_type=" + encodeURIComponent(rt) + "&check_in=" + ci + "&check_out=" + co, { headers: { "Accept": "application/json" } })
      .then(function (r) { return r.json(); })
      .then(function (q) {
        if (!q.ok) { box.innerHTML = "<p class='mb-0'>" + msg.select + "</p>"; return; }
        var html = "<div class='quote-row'><span>" + msg.nights + "</span><strong>" + q.nights + "</strong></div>" +
          "<div class='quote-row'><span>" + msg.rate + "</span><strong>" + fmt(q.price_per_night) + "</strong></div>" +
          "<div class='pt-3'>" + msg.total + "</div><div class='total'>" + fmt(q.total) + "</div>";
        html += q.available > 0
          ? "<p class='mt-2 mb-0 text-warning'><i class='fa-solid fa-circle-check'></i> " + msg.avail + "</p>"
          : "<p class='mt-2 mb-0 text-danger-emphasis' style='color:#ffb4b4'><i class='fa-solid fa-circle-xmark'></i> " + msg.full + "</p>";
        box.innerHTML = html;
      })
      .catch(function () { box.innerHTML = "<p class='mb-0'>" + msg.select + "</p>"; });
  }

  function schedule() { clearTimeout(timer); timer = setTimeout(refresh, 200); }
  ["room_type", "check_in", "check_out"].forEach(function (n) {
    form.querySelector("[name=" + n + "]").addEventListener("change", schedule);
  });
  refresh();
})();

/* Dashboard sidebar toggle (mobile) */
(function () {
  var btn = document.getElementById("dash-toggle");
  var side = document.getElementById("dash-side");
  if (btn && side) btn.addEventListener("click", function () { side.classList.toggle("open"); });
})();

/* Confirm destructive buttons */
document.addEventListener("click", function (e) {
  var el = e.target.closest("[data-confirm]");
  if (el && !window.confirm(el.getAttribute("data-confirm"))) e.preventDefault();
});
