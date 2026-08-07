import json


LANGUAGE_STORAGE_KEY = "cruxwledbridge.language"


def language_switch_html(translations):
    """Return the shared English/German language switch and translation runtime."""
    merged_translations = {
        "en": {
            "language.switch_to_de": "Switch to German",
            **translations.get("en", {}),
        },
        "de": {
            "language.switch_to_en": "Auf Englisch wechseln",
            **translations.get("de", {}),
        },
    }
    translations_json = json.dumps(
        merged_translations,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")

    html = r'''
        <style>
            .language-toggle {
                position: fixed;
                top: 12px;
                right: 12px;
                z-index: 1000;
                width: 38px;
                height: 32px;
                padding: 0;
                margin: 0;
                border: 1px solid rgba(0, 0, 0, 0.18);
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.94);
                color: inherit;
                font-size: 20px;
                line-height: 30px;
                text-align: center;
                cursor: pointer;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
            }
            .language-toggle:hover {
                background: #fff;
            }
            .language-toggle:focus-visible {
                outline: 3px solid #2684ff;
                outline-offset: 2px;
            }
        </style>
        <button
            id="language-toggle"
            class="language-toggle"
            type="button"
            aria-label="Switch to German"
            title="Switch to German"
        >🇩🇪</button>
        <script>
            (() => {
                const translations = __TRANSLATIONS__;
                const storageKey = '__STORAGE_KEY__';
                const supportedLanguages = ['en', 'de'];
                let savedLanguage = null;
                try {
                    savedLanguage = window.localStorage.getItem(storageKey);
                } catch (error) {
                    // Storage can be unavailable in privacy-restricted browsers.
                }
                let currentLanguage = supportedLanguages.includes(savedLanguage)
                    ? savedLanguage
                    : 'en';
                const toggle = document.getElementById('language-toggle');

                function translate(key, replacements = {}) {
                    let value = translations[currentLanguage]?.[key]
                        ?? translations.en?.[key]
                        ?? key;
                    for (const [name, replacement] of Object.entries(replacements)) {
                        value = value.replaceAll(`{${name}}`, String(replacement));
                    }
                    return value;
                }

                function applyLanguage(language, persist = false) {
                    currentLanguage = supportedLanguages.includes(language) ? language : 'en';
                    document.documentElement.lang = currentLanguage;

                    document.querySelectorAll('[data-i18n]').forEach((element) => {
                        element.textContent = translate(element.dataset.i18n);
                    });
                    for (const attribute of ['placeholder', 'title', 'alt', 'aria-label']) {
                        const dataAttribute = `data-i18n-${attribute}`;
                        document.querySelectorAll(`[${dataAttribute}]`).forEach((element) => {
                            element.setAttribute(attribute, translate(element.getAttribute(dataAttribute)));
                        });
                    }

                    const targetLanguage = currentLanguage === 'en' ? 'de' : 'en';
                    toggle.textContent = targetLanguage === 'de' ? '🇩🇪' : '🇬🇧';
                    const toggleLabel = translate(`language.switch_to_${targetLanguage}`);
                    toggle.setAttribute('aria-label', toggleLabel);
                    toggle.title = toggleLabel;

                    if (persist) {
                        try {
                            window.localStorage.setItem(storageKey, currentLanguage);
                        } catch (error) {
                            // The page remains usable even when storage is unavailable.
                        }
                    }
                }

                toggle.addEventListener('click', () => {
                    const nextLanguage = currentLanguage === 'en' ? 'de' : 'en';
                    applyLanguage(nextLanguage, true);
                    window.dispatchEvent(new CustomEvent('crux-language-change'));
                });

                window.cruxI18n = {
                    getLanguage: () => currentLanguage,
                    setLanguage: (language) => applyLanguage(language, true),
                    t: translate,
                };
                applyLanguage(currentLanguage);
            })();
        </script>
    '''
    return html.replace("__TRANSLATIONS__", translations_json).replace(
        "__STORAGE_KEY__",
        LANGUAGE_STORAGE_KEY,
    )
