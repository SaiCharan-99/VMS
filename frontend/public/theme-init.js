// Applies the saved theme before first paint. A file (not inline) so the CSP needs no hash.
try {
  var t = localStorage.getItem("vms.theme");
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
} catch (e) {}
