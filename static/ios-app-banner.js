(function() {
    "use strict";

    var APP_STORE_URL = "https://apps.apple.com/app/id6810203217";
    var DISMISS_KEY = "optiplein-ios-app-banner-dismissed-until";
    var DISMISS_DAYS = 7;

    function estAppNative() {
        var capacitor = window.Capacitor;
        return Boolean(
            capacitor
            && typeof capacitor.getPlatform === "function"
            && capacitor.getPlatform() === "ios"
        );
    }

    function estNavigationIOS() {
        var ua = navigator.userAgent || "";
        var platform = navigator.platform || "";

        return /iPhone|iPad|iPod/i.test(ua)
            || (
                /Mac/i.test(platform)
                && Number(navigator.maxTouchPoints || 0) > 1
            );
    }

    function banniereFermeeRecemment() {
        var expiration = Number(localStorage.getItem(DISMISS_KEY) || 0);
        return Number.isFinite(expiration) && expiration > Date.now();
    }

    function fermerBanniere(banniere) {
        banniere.hidden = true;
        localStorage.setItem(
            DISMISS_KEY,
            String(Date.now() + DISMISS_DAYS * 24 * 60 * 60 * 1000)
        );
    }

    function creerBanniere() {
        if (
            document.getElementById("ios-download-banner")
            || estAppNative()
            || !estNavigationIOS()
            || banniereFermeeRecemment()
        ) {
            return;
        }

        var banniere = document.createElement("aside");
        banniere.id = "ios-download-banner";
        banniere.className = "ios-download-banner";
        banniere.setAttribute("role", "region");
        banniere.setAttribute(
            "aria-label",
            "Télécharger l'application iPhone OptiPlein"
        );

        banniere.innerHTML = ''
            + '<img class="ios-download-banner-logo" src="/static/favicon.png" alt="">'
            + '<div class="ios-download-banner-copy">'
            + '<p class="ios-download-banner-title">OptiPlein est sur iPhone</p>'
            + '<p class="ios-download-banner-text">Installez l’app pour une expérience plus fluide.</p>'
            + '</div>'
            + '<a class="ios-download-banner-action" href="' + APP_STORE_URL + '" rel="noopener">Télécharger</a>'
            + '<button class="ios-download-banner-close" type="button" aria-label="Masquer la bannière">&times;</button>';

        banniere
            .querySelector(".ios-download-banner-close")
            .addEventListener("click", function() {
                fermerBanniere(banniere);
            });

        document.body.appendChild(banniere);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", creerBanniere);
    } else {
        creerBanniere();
    }
})();
