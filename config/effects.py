"""Все эффекты и анимации приложения."""


# =============================================================================
# ЭФФЕКТЫ ВРЕМЕНИ СУТОК
# =============================================================================

def get_morning_effect() -> str:
    """Эффект утреннего рассвета (мягкий свет)."""
    return (
        "<style>"
        ".morning-glow{position:fixed;top:0;left:0;width:100%;height:100%;background:radial-gradient(ellipse at top,rgba(241,148,138,0.15) 0%,transparent 70%);z-index:0;pointer-events:none}"
        "</style>"
        "<div class='morning-glow'></div>"
    )


def get_clouds_effect() -> str:
    """Эффект плывущих облаков."""
    return (
        "<style>"
        ".cloud{position:fixed;background:rgba(255,255,255,0.6);border-radius:100px;z-index:0;pointer-events:none;animation:cloudFloat linear infinite}"
        ".cloud::before,.cloud::after{content:'';position:absolute;background:rgba(255,255,255,0.6);border-radius:100px}"
        ".cloud:nth-child(1){width:100px;height:40px;top:20%;left:-100px;animation-duration:25s}"
        ".cloud:nth-child(1)::before{width:50px;height:50px;top:-25px;left:15px}"
        ".cloud:nth-child(1)::after{width:60px;height:40px;top:-15px;right:15px}"
        ".cloud:nth-child(2){width:80px;height:30px;top:40%;left:-80px;animation-duration:30s;animation-delay:5s}"
        ".cloud:nth-child(2)::before{width:40px;height:40px;top:-20px;left:10px}"
        ".cloud:nth-child(3){width:120px;height:45px;top:60%;left:-120px;animation-duration:35s;animation-delay:10s}"
        ".cloud:nth-child(3)::before{width:60px;height:50px;top:-25px;left:20px}"
        ".cloud:nth-child(3)::after{width:70px;height:45px;top:-20px;right:20px}"
        "@keyframes cloudFloat{0%{transform:translateX(0)}100%{transform:translateX(calc(100vw + 200px))}}"
        "</style>"
        "<div class='cloud'></div>"
        "<div class='cloud'></div>"
        "<div class='cloud'></div>"
    )


def get_stars_effect() -> str:
    """Эффект мерцающих звёзд."""
    return (
        "<style>"
        ".star{position:fixed;background:white;border-radius:50%;z-index:0;pointer-events:none;animation:twinkle ease-in-out infinite}"
        ".star:nth-child(1){width:2px;height:2px;top:10%;left:15%;animation-duration:3s}"
        ".star:nth-child(2){width:3px;height:3px;top:25%;left:45%;animation-duration:4s;animation-delay:1s}"
        ".star:nth-child(3){width:2px;height:2px;top:40%;left:75%;animation-duration:3.5s;animation-delay:2s}"
        ".star:nth-child(4){width:3px;height:3px;top:55%;left:25%;animation-duration:4.5s;animation-delay:0.5s}"
        ".star:nth-child(5){width:2px;height:2px;top:70%;left:60%;animation-duration:3s;animation-delay:1.5s}"
        ".star:nth-child(6){width:3px;height:3px;top:85%;left:85%;animation-duration:4s;animation-delay:2.5s}"
        ".star:nth-child(7){width:2px;height:2px;top:15%;left:90%;animation-duration:3.5s;animation-delay:0.8s}"
        ".star:nth-child(8){width:3px;height:3px;top:50%;left:10%;animation-duration:4s;animation-delay:1.2s}"
        "@keyframes twinkle{0%,100%{opacity:0.3;transform:scale(1)}50%{opacity:1;transform:scale(1.3)}}"
        "</style>"
        "<div class='star'></div>"
        "<div class='star'></div>"
        "<div class='star'></div>"
        "<div class='star'></div>"
        "<div class='star'></div>"
        "<div class='star'></div>"
        "<div class='star'></div>"
        "<div class='star'></div>"
    )


def get_sunset_effect() -> str:
    """Эффект закатного неба."""
    return (
        "<style>"
        ".sunset-glow{position:fixed;top:0;left:0;width:100%;height:100%;background:radial-gradient(ellipse at bottom,rgba(230,126,34,0.15) 0%,transparent 70%);z-index:0;pointer-events:none}"
        "</style>"
        "<div class='sunset-glow'></div>"
    )


def get_theme_effect(theme: str) -> str:
    """Возвращает эффекты для темы времени суток."""
    effects = {
        "morning": get_morning_effect(),  # Новый эффект для утра
        "day": get_clouds_effect(),
        "evening": get_sunset_effect(),
        "night": get_stars_effect(),
    }
    return effects.get(theme, "")


# =============================================================================
# ПРАЗДНИЧНЫЕ ЭФФЕКТЫ
# =============================================================================

def get_snow_effect() -> str:
    """Эффект падающего снега."""
    return (
        "<style>"
        ".snowflake{position:fixed;color:white;font-size:1.5em;z-index:0;pointer-events:none;animation:fall linear infinite}"
        ".snowflake:nth-child(1){left:10%;animation-duration:8s}"
        ".snowflake:nth-child(2){left:25%;animation-duration:10s;animation-delay:2s}"
        ".snowflake:nth-child(3){left:40%;animation-duration:9s;animation-delay:4s}"
        ".snowflake:nth-child(4){left:55%;animation-duration:11s;animation-delay:1s}"
        ".snowflake:nth-child(5){left:70%;animation-duration:8s;animation-delay:3s}"
        ".snowflake:nth-child(6){left:85%;animation-duration:10s;animation-delay:5s}"
        "@keyframes fall{0%{transform:translateY(-100px) rotate(0deg);opacity:1}100%{transform:translateY(100vh) rotate(360deg);opacity:0.3}}"
        "</style>"
        "<div class='snowflake'>❄</div>"
        "<div class='snowflake'>❅</div>"
        "<div class='snowflake'>❆</div>"
        "<div class='snowflake'>❄</div>"
        "<div class='snowflake'></div>"
        "<div class='snowflake'></div>"
    )


def get_confetti_effect() -> str:
    """Эффект падающего конфетти."""
    return (
        "<style>"
        ".confetti{position:fixed;width:10px;height:10px;z-index:0;pointer-events:none;animation:confettiFall linear infinite}"
        ".confetti:nth-child(1){left:10%;background:#E74C3C;animation-duration:6s}"
        ".confetti:nth-child(2){left:25%;background:#F1C40F;animation-duration:7s;animation-delay:1s}"
        ".confetti:nth-child(3){left:40%;background:#2ECC71;animation-duration:8s;animation-delay:2s}"
        ".confetti:nth-child(4){left:55%;background:#3498DB;animation-duration:6s;animation-delay:0.5s}"
        ".confetti:nth-child(5){left:70%;background:#9B59B6;animation-duration:9s;animation-delay:1.5s}"
        ".confetti:nth-child(6){left:85%;background:#E67E22;animation-duration:7s;animation-delay:3s}"
        "@keyframes confettiFall{0%{transform:translateY(-100px) rotate(0deg);opacity:1}100%{transform:translateY(100vh) rotate(720deg);opacity:0.5}}"
        "</style>"
        "<div class='confetti'></div>"
        "<div class='confetti'></div>"
        "<div class='confetti'></div>"
        "<div class='confetti'></div>"
        "<div class='confetti'></div>"
        "<div class='confetti'></div>"
    )


def get_falling_pizza_effect() -> str:
    """Эффект падающей пиццы."""
    return (
        "<style>"
        ".falling-pizza{position:fixed;font-size:2em;z-index:0;pointer-events:none;animation:pizzaFall linear infinite}"
        ".falling-pizza:nth-child(1){left:15%;animation-duration:7s}"
        ".falling-pizza:nth-child(2){left:35%;animation-duration:9s;animation-delay:1s}"
        ".falling-pizza:nth-child(3){left:55%;animation-duration:8s;animation-delay:3s}"
        ".falling-pizza:nth-child(4){left:75%;animation-duration:10s;animation-delay:2s}"
        "@keyframes pizzaFall{0%{transform:translateY(-100px) rotate(0deg);opacity:1}100%{transform:translateY(100vh) rotate(720deg);opacity:0.5}}"
        "</style>"
        "<div class='falling-pizza'>🍕</div>"
        "<div class='falling-pizza'></div>"
        "<div class='falling-pizza'>🍕</div>"
        "<div class='falling-pizza'></div>"
    )


def get_pumpkins_effect() -> str:
    """Эффект парящих тыкв."""
    return (
        "<style>"
        ".pumpkin{position:fixed;font-size:2.5em;z-index:0;pointer-events:none;animation:pumpkinFloat 4s ease-in-out infinite}"
        ".pumpkin:nth-child(1){top:20%;left:5%}"
        ".pumpkin:nth-child(2){top:40%;right:10%;animation-delay:1s}"
        ".pumpkin:nth-child(3){bottom:20%;left:15%;animation-delay:2s}"
        "@keyframes pumpkinFloat{0%,100%{transform:translateY(0) rotate(-5deg)}50%{transform:translateY(-20px) rotate(5deg)}}"
        "</style>"
        "<div class='pumpkin'></div>"
        "<div class='pumpkin'></div>"
        "<div class='pumpkin'>🎃</div>"
    )


def get_hearts_effect() -> str:
    """Эффект парящих сердечек."""
    return (
        "<style>"
        ".heart{position:fixed;font-size:1.5em;z-index:0;pointer-events:none;animation:heartFloat linear infinite}"
        ".heart:nth-child(1){left:10%;animation-duration:6s}"
        ".heart:nth-child(2){left:30%;animation-duration:8s;animation-delay:1s}"
        ".heart:nth-child(3){left:50%;animation-duration:7s;animation-delay:2s}"
        ".heart:nth-child(4){left:70%;animation-duration:9s;animation-delay:0.5s}"
        ".heart:nth-child(5){left:90%;animation-duration:6s;animation-delay:1.5s}"
        "@keyframes heartFloat{0%{transform:translateY(100vh) scale(0);opacity:0}10%{opacity:1}90%{opacity:1}100%{transform:translateY(-100px) scale(1.5);opacity:0}}"
        "</style>"
        "<div class='heart'>❤️</div>"
        "<div class='heart'></div>"
        "<div class='heart'>💖</div>"
        "<div class='heart'>💗</div>"
        "<div class='heart'>💝</div>"
    )


def get_leaves_effect() -> str:
    """Эффект падающих листьев."""
    return (
        "<style>"
        ".leaf{position:fixed;font-size:1.5em;z-index:0;pointer-events:none;animation:leafFall linear infinite}"
        ".leaf:nth-child(1){left:15%;animation-duration:8s}"
        ".leaf:nth-child(2){left:35%;animation-duration:10s;animation-delay:2s}"
        ".leaf:nth-child(3){left:55%;animation-duration:9s;animation-delay:4s}"
        ".leaf:nth-child(4){left:75%;animation-duration:11s;animation-delay:1s}"
        ".leaf:nth-child(5){left:90%;animation-duration:8s;animation-delay:3s}"
        "@keyframes leafFall{0%{transform:translateY(-100px) rotate(0deg) translateX(0);opacity:1}100%{transform:translateY(100vh) rotate(720deg) translateX(100px);opacity:0.3}}"
        "</style>"
        "<div class='leaf'>🍂</div>"
        "<div class='leaf'>🍁</div>"
        "<div class='leaf'>🍃</div>"
        "<div class='leaf'></div>"
        "<div class='leaf'>🍁</div>"
    )


def get_fireworks_effect() -> str:
    """Эффект фейерверка."""
    return (
        "<style>"
        ".firework{position:fixed;width:4px;height:4px;border-radius:50%;z-index:0;pointer-events:none;animation:fireworkExplode 2s ease-out infinite}"
        ".firework:nth-child(1){top:30%;left:20%;background:#E74C3C;animation-delay:0s}"
        ".firework:nth-child(2){top:40%;left:50%;background:#F1C40F;animation-delay:0.5s}"
        ".firework:nth-child(3){top:25%;left:80%;background:#2ECC71;animation-delay:1s}"
        ".firework:nth-child(4){top:50%;left:35%;background:#3498DB;animation-delay:1.5s}"
        ".firework:nth-child(5){top:35%;left:65%;background:#9B59B6;animation-delay:0.3s}"
        "@keyframes fireworkExplode{0%{transform:scale(0);opacity:1;box-shadow:0 0 0 0 currentColor}50%{transform:scale(1);opacity:1;box-shadow:0 0 20px 10px currentColor}100%{transform:scale(0);opacity:0;box-shadow:0 0 0 0 currentColor}}"
        "</style>"
        "<div class='firework'></div>"
        "<div class='firework'></div>"
        "<div class='firework'></div>"
        "<div class='firework'></div>"
        "<div class='firework'></div>"
    )


def get_rain_effect() -> str:
    """Эффект дождя."""
    return (
        "<style>"
        ".raindrop{position:fixed;width:2px;height:20px;background:linear-gradient(to bottom,transparent,rgba(174,194,224,0.6));z-index:0;pointer-events:none;animation:rainFall linear infinite}"
        ".raindrop:nth-child(1){left:10%;animation-duration:1s}"
        ".raindrop:nth-child(2){left:20%;animation-duration:1.2s;animation-delay:0.1s}"
        ".raindrop:nth-child(3){left:30%;animation-duration:0.9s;animation-delay:0.2s}"
        ".raindrop:nth-child(4){left:40%;animation-duration:1.1s;animation-delay:0.3s}"
        ".raindrop:nth-child(5){left:50%;animation-duration:1s;animation-delay:0.4s}"
        ".raindrop:nth-child(6){left:60%;animation-duration:1.3s;animation-delay:0.5s}"
        ".raindrop:nth-child(7){left:70%;animation-duration:0.8s;animation-delay:0.6s}"
        ".raindrop:nth-child(8){left:80%;animation-duration:1.1s;animation-delay:0.7s}"
        ".raindrop:nth-child(9){left:90%;animation-duration:1s;animation-delay:0.8s}"
        "@keyframes rainFall{0%{transform:translateY(-100px);opacity:1}100%{transform:translateY(100vh);opacity:0.3}}"
        "</style>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
        "<div class='raindrop'></div>"
    )


# =============================================================================
# СБОРЩИК ЭФФЕКТОВ
# =============================================================================

HOLIDAY_EFFECTS = {
    "snow": get_snow_effect,
    "confetti": get_confetti_effect,
    "falling_pizza": get_falling_pizza_effect,
    "pumpkins": get_pumpkins_effect,
    "hearts": get_hearts_effect,
    "leaves": get_leaves_effect,
    "fireworks": get_fireworks_effect,
    "rain": get_rain_effect,
}


def get_holiday_effect(effect_name: str) -> str:
    """Возвращает CSS и HTML для одного праздничного эффекта."""
    effect_func = HOLIDAY_EFFECTS.get(effect_name)
    if effect_func:
        return effect_func()
    return ""


def get_holiday_effects(effects_list: list) -> str:
    """Возвращает CSS и HTML для списка праздничных эффектов."""
    if not effects_list:
        return ""
    
    result = ""
    for effect_name in effects_list:
        result += get_holiday_effect(effect_name)
    
    return result
