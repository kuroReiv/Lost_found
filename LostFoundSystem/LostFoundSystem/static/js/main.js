// Sidebar pada layar kecil
(function () {
  var toggle = document.getElementById("sidebarToggle");
  var sidebar = document.getElementById("sidebar");
  var backdrop = document.getElementById("sideBackdrop");
  if (toggle && sidebar && backdrop) {
    var tutup = function () { sidebar.classList.remove("open"); backdrop.classList.remove("show"); };
    toggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      backdrop.classList.toggle("show");
    });
    backdrop.addEventListener("click", tutup);
  }

  // Pratinjau foto sebelum diunggah + cek ukuran (maks 2 MB)
  var input = document.getElementById("fotoInput");
  var preview = document.getElementById("fotoPreview");
  if (input) {
    input.addEventListener("change", function () {
      var file = input.files[0];
      if (!file) { if (preview) preview.classList.add("d-none"); return; }
      if (file.size > 2 * 1024 * 1024) {
        alert("Ukuran foto maksimal 2 MB.");
        input.value = "";
        return;
      }
      if (preview) {
        preview.src = URL.createObjectURL(file);
        preview.classList.remove("d-none");
      }
    });
  }
})();
