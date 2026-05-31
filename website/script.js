(function () {
  "use strict";

  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");

  if (toggle && nav) {
    function setOpen(open) {
      nav.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      setOpen(!nav.classList.contains("is-open"));
    });

    nav.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener("click", function () {
        setOpen(false);
      });
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        setOpen(false);
      }
    });

    window.addEventListener("resize", function () {
      if (window.matchMedia("(min-width: 901px)").matches) {
        setOpen(false);
      }
    });
  }
})();

(function () {
  "use strict";

  var figures = document.querySelectorAll(".env-figure");
  if (!figures.length) {
    return;
  }

  var lang = document.documentElement.lang || "en";
  var labels = {
    en: {
      open: "View full size",
      close: "Close",
    },
    ru: {
      open: "Открыть в полном размере",
      close: "Закрыть",
    },
  };
  var t = labels[lang] || labels.en;

  var dialog = document.createElement("dialog");
  dialog.className = "env-lightbox";
  dialog.innerHTML =
    '<button type="button" class="env-lightbox__close" aria-label="' +
    t.close +
    '">&times;</button>' +
    '<figure class="env-lightbox__figure">' +
    '<img class="env-lightbox__img" alt="">' +
    '<figcaption class="env-lightbox__caption"></figcaption>' +
    "</figure>";
  document.body.appendChild(dialog);

  var lightImg = dialog.querySelector(".env-lightbox__img");
  var lightCaption = dialog.querySelector(".env-lightbox__caption");
  var closeBtn = dialog.querySelector(".env-lightbox__close");

  function openLightbox(img, caption) {
    lightImg.src = img.currentSrc || img.src;
    lightImg.alt = img.alt;
    lightCaption.textContent = caption;
    lightCaption.hidden = !caption;
    dialog.showModal();
  }

  function closeLightbox() {
    if (dialog.open) {
      dialog.close();
    }
  }

  figures.forEach(function (figure) {
    var img = figure.querySelector("img");
    if (!img) {
      return;
    }

    var captionEl = figure.querySelector("figcaption");
    var caption = captionEl ? captionEl.textContent.trim() : "";

    var trigger = figure.querySelector(".env-figure__open");
    if (!trigger) {
      trigger = document.createElement("button");
      trigger.type = "button";
      trigger.className = "env-figure__open";
      img.parentNode.insertBefore(trigger, img);
      trigger.appendChild(img);
    }

    if (!trigger.getAttribute("aria-label")) {
      trigger.setAttribute("aria-label", caption ? t.open + ": " + caption : t.open);
    }

    trigger.addEventListener("click", function () {
      openLightbox(img, caption);
    });
  });

  closeBtn.addEventListener("click", closeLightbox);

  dialog.addEventListener("click", function (e) {
    if (e.target === lightImg) {
      return;
    }
    closeLightbox();
  });

  dialog.addEventListener("close", function () {
    lightImg.removeAttribute("src");
  });
})();
