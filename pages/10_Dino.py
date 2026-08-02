import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone, timedelta

# Настройка страницы
st.set_page_config(
    page_title="Дино-Ловец",
    page_icon="🦖",
    layout="wide"
)

# Время UTC+3
MOSCOW_TZ = timezone(timedelta(hours=3))
current_time = datetime.now(MOSCOW_TZ)

# Цвета бренда (из config/brand.py)
BRAND_COLORS = {
    "primary": "#FF6B6B",
    "secondary": "#4ECDC4",
    "accent": "#FFE66D",
    "dark": "#2C3E50",
    "light": "#ECF0F1"
}

# Заголовок
st.markdown(f"""
<div style='text-align: center; padding: 2rem 0;'>
    <h1 style='color: {BRAND_COLORS["primary"]}; font-size: 3rem; margin-bottom: 0.5rem;'>
        🦖 Дино-Ловец 🎮
    </h1>
    <p style='color: {BRAND_COLORS["dark"]}; font-size: 1.2rem;'>
        Помоги Дино собрать хорошие отзывы и уклониться от плохих!
    </p>
    <p style='color: {BRAND_COLORS["secondary"]}; font-size: 0.9rem;'>
        Управление: ← → (стрелки) или A/D | Текущее время: {current_time.strftime('%H:%M:%S')}
    </p>
</div>
""", unsafe_allow_html=True)

# HTML/JS код игры
game_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset='UTF-8'>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Arial', sans-serif; 
            background: linear-gradient(135deg, {BRAND_COLORS["light"]} 0%, #ffffff 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }}
        #gameContainer {{
            position: relative;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            border-radius: 15px;
            overflow: hidden;
        }}
        canvas {{
            display: block;
            background: linear-gradient(180deg, #87CEEB 0%, #E0F6FF 100%);
            border: 4px solid {BRAND_COLORS["primary"]};
        }}
        #scoreBoard {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255,255,255,0.95);
            padding: 15px 25px;
            border-radius: 10px;
            font-size: 20px;
            font-weight: bold;
            color: {BRAND_COLORS["dark"]};
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        #gameOver {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255,255,255,0.98);
            padding: 40px 60px;
            border-radius: 20px;
            text-align: center;
            display: none;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        #gameOver h2 {{
            color: {BRAND_COLORS["primary"]};
            font-size: 36px;
            margin-bottom: 20px;
        }}
        #gameOver p {{
            color: {BRAND_COLORS["dark"]};
            font-size: 24px;
            margin-bottom: 30px;
        }}
        #restartBtn {{
            background: {BRAND_COLORS["primary"]};
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 20px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }}
        #restartBtn:hover {{
            background: {BRAND_COLORS["secondary"]};
            transform: scale(1.05);
        }}
        #instructions {{
            margin-top: 20px;
            text-align: center;
            color: {BRAND_COLORS["dark"]};
            font-size: 16px;
            background: rgba(255,255,255,0.9);
            padding: 15px 30px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div id="gameContainer">
        <canvas id="gameCanvas" width="800" height="600"></canvas>
        <div id="scoreBoard">Счёт: <span id="score">0</span></div>
        <div id="gameOver">
            <h2>🦖 Игра окончена!</h2>
            <p>Ваш счёт: <span id="finalScore">0</span></p>
            <button id="restartBtn">Играть снова</button>
        </div>
    </div>
    <div id="instructions">
        <strong>Управление:</strong> ← → (стрелки) или A/D для движения | 
        <strong>Цель:</strong> Ловите ⭐🍕💰 и избегайте 💢😡
    </div>

    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const gameOverElement = document.getElementById('gameOver');
        const finalScoreElement = document.getElementById('finalScore');
        const restartBtn = document.getElementById('restartBtn');

        // Игровые переменные
        let dino = {{
            x: canvas.width / 2 - 25,
            y: canvas.height - 80,
            width: 50,
            height: 50,
            speed: 8
        }};

        let objects = [];
        let score = 0;
        let gameRunning = true;
        let keys = {{}};
        let spawnTimer = 0;
        let spawnInterval = 60;

        // Типы объектов
        const objectTypes = [
            {{ emoji: '⭐', type: 'good', points: 10 }},
            {{ emoji: '🍕', type: 'good', points: 15 }},
            {{ emoji: '💰', type: 'good', points: 20 }},
            {{ emoji: '💢', type: 'bad', points: -10 }},
            {{ emoji: '😡', type: 'bad', points: -15 }},
            {{ emoji: '📉', type: 'bad', points: -20 }}
        ];

        // Обработка клавиш
        document.addEventListener('keydown', (e) => {{
            keys[e.key] = true;
        }});

        document.addEventListener('keyup', (e) => {{
            keys[e.key] = false;
        }});

        restartBtn.addEventListener('click', restartGame);

        // Создание объекта
        function spawnObject() {{
            const type = objectTypes[Math.floor(Math.random() * objectTypes.length)];
            objects.push({{
                x: Math.random() * (canvas.width - 40),
                y: -40,
                width: 40,
                height: 40,
                speed: 3 + Math.random() * 2,
                emoji: type.emoji,
                type: type.type,
                points: type.points
            }});
        }}

        // Отрисовка Дино
        function drawDino() {{
            ctx.font = '50px Arial';
            ctx.fillText('🦖', dino.x, dino.y + 50);
        }}

        // Отрисовка объектов
        function drawObjects() {{
            objects.forEach(obj => {{
                ctx.font = '40px Arial';
                ctx.fillText(obj.emoji, obj.x, obj.y + 40);
            }});
        }}

        // Обновление игры
        function update() {{
            if (!gameRunning) return;

            // Движение Дино
            if ((keys['ArrowLeft'] || keys['a'] || keys['A']) && dino.x > 0) {{
                dino.x -= dino.speed;
            }}
            if ((keys['ArrowRight'] || keys['d'] || keys['D']) && dino.x < canvas.width - dino.width) {{
                dino.x += dino.speed;
            }}

            // Создание новых объектов
            spawnTimer++;
            if (spawnTimer > spawnInterval) {{
                spawnObject();
                spawnTimer = 0;
                // Увеличиваем сложность
                if (spawnInterval > 30) {{
                    spawnInterval -= 0.5;
                }}
            }}

            // Обновление объектов
            objects.forEach((obj, index) => {{
                obj.y += obj.speed;

                // Проверка столкновения с Дино
                if (obj.y + obj.height >= dino.y &&
                    obj.y <= dino.y + dino.height &&
                    obj.x + obj.width >= dino.x &&
                    obj.x <= dino.x + dino.width) {{
                    
                    score += obj.points;
                    if (score < 0) score = 0;
                    scoreElement.textContent = score;
                    objects.splice(index, 1);

                    // Game over при столкновении с плохим объектом
                    if (obj.type === 'bad' && obj.points <= -20) {{
                        gameOver();
                    }}
                }}

                // Удаление объектов за пределами экрана
                if (obj.y > canvas.height) {{
                    objects.splice(index, 1);
                }}
            }});
        }}

        // Отрисовка
        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Фон
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, '#87CEEB');
            gradient.addColorStop(1, '#E0F6FF');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            drawDino();
            drawObjects();
        }}

        // Игровой цикл
        function gameLoop() {{
            update();
            draw();
            if (gameRunning) {{
                requestAnimationFrame(gameLoop);
            }}
        }}

        // Game Over
        function gameOver() {{
            gameRunning = false;
            finalScoreElement.textContent = score;
            gameOverElement.style.display = 'block';
        }}

        // Перезапуск
        function restartGame() {{
            dino.x = canvas.width / 2 - 25;
            objects = [];
            score = 0;
            spawnInterval = 60;
            spawnTimer = 0;
            scoreElement.textContent = score;
            gameOverElement.style.display = 'none';
            gameRunning = true;
            gameLoop();
        }}

        // Запуск игры
        gameLoop();
    </script>
</body>
</html>
"""

# Встраивание игры
components.html(game_html, height=750, scrolling=False)

# Дополнительная информация
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; padding: 1rem; background: {BRAND_COLORS["light"]}; border-radius: 10px; margin-top: 1rem;'>
    <h3 style='color: {BRAND_COLORS["primary"]};'>🎯 Как играть</h3>
    <p style='color: {BRAND_COLORS["dark"]}; font-size: 1rem;'>
        ⭐ Звезда = 10 очков | 🍕 Пицца = 15 очков | 💰 Деньги = 20 очков<br>
        💢 Злость = -10 очков | 😡 Гнев = -15 очков | 📉 Падение = Game Over!<br><br>
        <strong>Совет:</strong> Собирайте хорошие объекты и избегайте плохие. Чем дольше играете, тем быстрее падают объекты!
    </p>
</div>
""", unsafe_allow_html=True)