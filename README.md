# Just experiment... not intended to public use.

# Todo
- Multidir: Skip if folder exist (vždy => nedělat to nastavitelné!!!)
- Downloader: Accept cookies/rules... autmatically
- Config: Option to set secure/unsecure search
- odladit `pkl` chybu
- odladit chybu `str` on `null`

## Tip
- ukládat, kde jsme skončili a příště navázat
    * nový log `yandex.yml` místo json
    * ukládat poslední úspěšně staženou položku do `- last: url|keyword`
    * ukládat úspěšně stažená url `- done: - image_url`
        - kvůli znovupoužití v turbo režimu
        - vynechat pokud je v negative
