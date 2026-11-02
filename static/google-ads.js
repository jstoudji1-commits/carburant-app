/* Google Ads: basic consent mode. No Google request before consent. */
(function () {
    'use strict';
    if (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) return;
    var tagId = 'AW-18540838649';
    var destination = tagId + '/bgDvCM746KsdEPn9-ohF';
    var cookieName = 'optiplein_ads_consent';
    var loaded = false;
    var inFlight = new Set();
    function consent() {
        var match = document.cookie.split('; ').find(function (part) {return part.indexOf(cookieName + '=') === 0;});
        return match ? match.split('=')[1] : '';
    }
    window.dataLayer = window.dataLayer || [];
    function tag() {window.dataLayer.push(arguments);}
    tag('consent', 'default', {ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied', analytics_storage:'denied'});
    function cleanUrl(value) {
        try {
            var url = new URL(value);
            var safe = new URL(url.origin + url.pathname);
            ['gclid','gbraid','wbraid','utm_source','utm_medium','utm_campaign'].forEach(function (key) {
                if (url.searchParams.has(key)) safe.searchParams.set(key, url.searchParams.get(key));
            });
            return safe.href;
        } catch (_) {return '';}
    }
    async function conversions() {
        if (consent() !== 'granted') return;
        try {
            var response = await fetch('/api/ads/conversions', {credentials:'same-origin', cache:'no-store'});
            if (!response.ok || consent() !== 'granted') return;
            var data = await response.json();
            (data.conversions || []).forEach(function (item) {
                if (!['compte','testeur'].includes(item.kind) || !/^[A-Za-z0-9_-]{32}$/.test(item.id)) return;
                var key = 'optiplein-ads-sent-' + item.id;
                var sent = false;
                try {sent = localStorage.getItem(key) === '1';} catch (_) {}
                if (sent || inFlight.has(item.id) || consent() !== 'granted') return;
                inFlight.add(item.id);
                tag('event', 'conversion', {
                    send_to:destination, transaction_id:item.id,
                    event_callback:function () {
                        try {localStorage.setItem(key, '1');} catch (_) {}
                    }
                });
            });
        } catch (_) { /* Retry on a later page load, keeping the same transaction ID. */ }
    }
    function enable() {
        tag('consent', 'update', {ad_storage:'granted', ad_user_data:'granted', ad_personalization:'denied', analytics_storage:'denied'});
        if (!loaded) {
            loaded = true;
            tag('js', new Date());
            tag('config', tagId, {allow_ad_personalization_signals:false, page_location:cleanUrl(location.href), page_referrer:cleanUrl(document.referrer)});
            var script = document.createElement('script');
            script.async = true;
            script.src = 'https://www.googletagmanager.com/gtag/js?id=' + tagId;
            script.onload = conversions;
            document.head.appendChild(script);
        } else conversions();
    }
    var panel = document.createElement('section');
    panel.className = 'opti-ads-consent';
    panel.setAttribute('aria-label', 'Mesure publicitaire');
    panel.innerHTML = '<p>Autoriser la mesure des inscriptions avec Google Ads ? Avec votre accord, Google utilise des cookies pour relier vos visites et inscriptions à nos annonces. Le refus ne bloque aucune fonction d’OptiPlein.</p><a href="/confidentialite">Confidentialité</a><div><button type="button" data-choice="denied">Refuser</button><button type="button" data-choice="granted">Accepter</button></div>';
    panel.hidden = Boolean(consent());
    var settings = document.createElement('button');
    settings.type = 'button';
    settings.className = 'opti-ads-settings';
    settings.textContent = 'Mesure publicitaire';
    settings.onclick = function () {panel.hidden = false;};
    panel.querySelectorAll('[data-choice]').forEach(function (button) {
        button.onclick = function () {
            var choice = button.dataset.choice;
            document.cookie = cookieName + '=' + choice + '; Max-Age=15552000; Path=/; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');
            panel.hidden = true;
            if (choice === 'granted') enable();
            else {
                tag('consent', 'update', {ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied', analytics_storage:'denied'});
                // Unload the tag on withdrawal; future pages stay blocked.
                if (loaded) location.reload();
            }
        };
    });
    document.body.appendChild(panel);
    document.body.appendChild(settings);
    if (consent() === 'granted') enable();
})();
