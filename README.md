# magnesia.com.tr

Menderes Magnesiası (Magnesia ad Maeandrum) antik kentini tanıtan tek sayfalık statik web sitesi.

- Tüm site tek dosyadır: `index.html` (CSS ve JS içinde gömülü, görseller SVG çizim).
- Herhangi bir statik barındırmaya (GitHub Pages, Cloudflare Pages, Netlify, klasik hosting) doğrudan yüklenebilir.

## Diller

Türkçe sayfa (`index.html`) asıl kaynaktır. Diğer diller (`/en/`, `/de/`, `/fr/`, `/it/`, `/es/`, `/ru/`, `/zh/`, `/ja/`) ondan üretilir:

1. Türkçe `index.html` dosyasını düzenleyin.
2. `python3 i18n/build.py extract` çalıştırın; çevrilecek metinler `i18n/strings.tr.json` dosyasına yazılır.
3. Yeni/değişen metinlerin çevirilerini `i18n/<dil>.json` dosyalarına aynı sırayla ekleyin.
4. `python3 i18n/build.py build` ile dil sayfalarını yeniden üretin (eksik çeviri varsa betik hangi metin olduğunu söyler).

Akademik yayın başlıkları özgün dilinde bırakılır (`i18n/keep.json`). Dil sayfaları elle düzenlenmemelidir; bir sonraki derlemede üzerine yazılır.
