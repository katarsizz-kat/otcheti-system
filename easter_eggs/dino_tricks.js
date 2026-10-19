// Пасхалки главной страницы. dino.py встраивает этот код <script>-ом прямо
// в документ приложения: обработчики из iframe components.html умирают,
// когда Streamlit пересоздаёт iframe (например, при смене страницы).
// Плейсхолдеры __ROAR_URL__ и __WALK_ENABLED__ подставляет dino.py.
(function () {
  const P = window;
  const D = document;
  const ROAR_URL = P.location.origin + "/__ROAR_URL__";
  const WALK_ENABLED = __WALK_ENABLED__;
  const WALK_CHANCE = 0.2;

  // Документ приложения живёт, пока открыта вкладка — ставим слушатели один раз.
  if (P.__dinoTricksInstalled) return;
  P.__dinoTricksInstalled = true;

  const reducedMotion = P.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const cursorSvg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'>" +
    "<text y='26' font-size='26'>🦖</text></svg>";
  const cursorUrl = "data:image/svg+xml;utf8," + encodeURIComponent(cursorSvg);

  const style = D.createElement("style");
  style.textContent =
    ".dino-run { position: fixed; left: 100vw; z-index: 99999;" +
    "  pointer-events: none; line-height: 1;" +
    "  animation-name: dino-run; animation-timing-function: linear;" +
    "  animation-fill-mode: forwards; }" +
    "@keyframes dino-run { to { transform: translateX(calc(-100vw - 160px)); } }" +
    ".dino-run span { display: inline-block;" +
    "  animation: dino-hop 0.3s ease-in-out infinite alternate; }" +
    "@keyframes dino-hop { to { transform: translateY(-12px) rotate(-6deg); } }" +
    "body.dino-mode, body.dino-mode * {" +
    "  cursor: url(\"" + cursorUrl + "\") 4 4, auto !important; }";
  D.head.appendChild(style);

  function roar() {
    try {
      const audio = new P.Audio(ROAR_URL);
      audio.volume = 0.8;
      audio.play().catch(function () {});
    } catch (e) {}
  }

  // Один динозавр, бегущий справа налево (эмодзи 🦖 смотрит влево).
  function spawnDino(opts) {
    const el = D.createElement("div");
    el.className = "dino-run";
    el.style.top = opts.top;
    el.style.fontSize = opts.size + "px";
    el.style.animationDuration = opts.duration + "s";
    el.style.animationDelay = opts.delay + "s";
    el.innerHTML = "<span>🦖</span>";
    el.firstChild.style.animationDuration = opts.hop + "s";
    el.addEventListener("animationend", function (e) {
      if (e.target === el) el.remove();
    });
    D.body.appendChild(el);
  }

  // ----- 1. Konami-код: стайка динозавров под рык -----
  function stampede() {
    roar();
    if (reducedMotion) return;
    for (let i = 0; i < 14; i++) {
      spawnDino({
        top: (8 + Math.random() * 78).toFixed(1) + "vh",
        size: Math.round(32 + Math.random() * 40),
        duration: (2.2 + Math.random() * 1.8).toFixed(2),
        delay: (i * 0.12 + Math.random() * 0.3).toFixed(2),
        hop: (0.22 + Math.random() * 0.15).toFixed(2),
      });
    }
  }

  // e.code не зависит от раскладки: B и A сработают и на русской.
  const KONAMI = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown",
    "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "KeyB", "KeyA"];
  let konamiPos = 0;
  D.addEventListener("keydown", function (e) {
    if (e.code === KONAMI[konamiPos]) {
      konamiPos++;
      if (konamiPos === KONAMI.length) {
        konamiPos = 0;
        stampede();
      }
    } else {
      konamiPos = e.code === KONAMI[0] ? 1 : 0;
    }
  });

  // ----- 2. 10 кликов по заголовку: режим динозавра -----
  const DINO_GREETING = "Рррр, привет! 🦖";
  let dinoMode = false;
  let titleClicks = 0;
  let clickTimer = null;

  function applyGreeting() {
    D.querySelectorAll(".welcome-title").forEach(function (h) {
      if (dinoMode) {
        if (!h.dataset.original) h.dataset.original = h.textContent;
        if (h.textContent !== DINO_GREETING) h.textContent = DINO_GREETING;
      } else if (h.dataset.original) {
        h.textContent = h.dataset.original;
        delete h.dataset.original;
      }
    });
  }

  // Streamlit перерисовывает блоки при каждом rerun — возвращаем приветствие.
  new P.MutationObserver(function () {
    if (dinoMode) applyGreeting();
  }).observe(D.body, { childList: true, subtree: true });

  D.addEventListener("click", function (e) {
    if (!e.target.closest || !e.target.closest(".app-title")) return;
    titleClicks++;
    clearTimeout(clickTimer);
    clickTimer = setTimeout(function () { titleClicks = 0; }, 3000);
    if (titleClicks >= 10) {
      titleClicks = 0;
      dinoMode = !dinoMode;
      D.body.classList.toggle("dino-mode", dinoMode);
      applyGreeting();
      if (dinoMode) roar();
    }
  });

  // ----- 6. Редкая прогулка динозавра по низу экрана -----
  if (WALK_ENABLED && !reducedMotion && Math.random() < WALK_CHANCE) {
    P.setTimeout(function () {
      spawnDino({ top: "calc(100vh - 56px)", size: 36, duration: 16, delay: 0, hop: 0.45 });
    }, 3000 + Math.random() * 7000);
  }
})();
