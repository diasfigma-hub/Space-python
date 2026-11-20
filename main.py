"""Космические войны лололошек — простая аркада на Pygame."""

import os
import random

import pygame as pg

# ----------------------------------------------------------------------
#  Настройки игры
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIDTH, HEIGHT = 1280, 720
FPS = 60

WHITE = (255, 255, 255)
CYAN = (90, 210, 255)
RED = (255, 90, 90)
TEXT_DIM = (150, 165, 195)

PLAYER_SPEED = 340          # скорость корабля, пикселей в секунду
BOOST_SPEED = 560           # скорость корабля с ускорением на Space
BULLET_SPEED = 900          # скорость пули
SHOOT_DELAY = 0.16          # пауза между выстрелами
ASTEROID_SPEED = (90, 140)  # астероид летит со случайной скоростью из этого диапазона
SPAWN_DELAY = 0.9           # раз в столько секунд появляется новый астероид

pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("Космические войны лололошек")
clock = pg.time.Clock()


# ----------------------------------------------------------------------
#  Картинки. Путь собирается от папки с main.py, поэтому игру можно
#  запускать из любого места.
# ----------------------------------------------------------------------
def load_image(folder, name, size):
    path = os.path.join(BASE_DIR, "assets", folder, name)
    image = pg.image.load(path).convert_alpha()
    return pg.transform.scale(image, size)


SHIP_SIZE = (64, 128)
ship_idle = load_image("SpaceShip", "spaceship1.png", SHIP_SIZE)    # корабль стоит
ship_fly = load_image("SpaceShip", "spaceship3.png", SHIP_SIZE)     # корабль летит
ship_boost = load_image("SpaceShip", "spaceship5.png", SHIP_SIZE)   # корабль ускорился

# три картинки астероида: целый, треснутый, обломки
asteroid_images = [
    load_image("Asteroid", "Asteroid1.png", (64, 64)),
    load_image("Asteroid", "Asteroid2.png", (64, 64)),
    load_image("Asteroid", "Asteroid3.png", (64, 64)),
]

bullet_image = load_image("Bull", "bull1.png", (14, 30))

# ----------------------------------------------------------------------
#  Шрифты
# ----------------------------------------------------------------------
font_title = pg.font.SysFont("arial", 64, bold=True)
font_big = pg.font.SysFont("arial", 42, bold=True)
font_hud = pg.font.SysFont("arial", 26, bold=True)
font_button = pg.font.SysFont("arial", 30, bold=True)
font_small = pg.font.SysFont("arial", 20)


# ----------------------------------------------------------------------
#  Фон: тёмный космос со статичными звёздами.
#  Рисуем его один раз в начале, потом просто копируем на экран.
# ----------------------------------------------------------------------
background = pg.Surface((WIDTH, HEIGHT))
background.fill((6, 7, 20))
for i in range(160):
    x = random.randint(0, WIDTH)
    y = random.randint(0, HEIGHT)
    size = random.choice([1, 1, 2, 3])
    brightness = 70 + size * 50   # крупные звёзды светлее мелких
    pg.draw.circle(background, (brightness, brightness, 255), (x, y), size)


# ----------------------------------------------------------------------
#  Состояние игры
#  state хранит текущий экран: "menu", "playing", "paused" или "over"
# ----------------------------------------------------------------------
state = "menu"

player_x = WIDTH / 2
player_y = HEIGHT - 160
lives = 3
score = 0

asteroids = []   # каждый астероид это список [x, y, скорость, прочность]
bullets = []     # каждая пуля это список [x, y]

spawn_timer = SPAWN_DELAY
shoot_timer = 0

# Кнопки меню и экранов
play_rect = pg.Rect(WIDTH // 2 - 170, 410, 340, 66)

resume_rect = pg.Rect(WIDTH // 2 - 170, 360, 340, 64)
pause_menu_rect = pg.Rect(WIDTH // 2 - 170, 442, 340, 64)

again_rect = pg.Rect(WIDTH // 2 - 170, 430, 340, 64)
finish_menu_rect = pg.Rect(WIDTH // 2 - 170, 512, 340, 64)


def reset_game():
    """Возвращает игру в начальное состояние перед новым заходом."""
    global player_x, player_y, lives, score, asteroids, bullets
    global spawn_timer, shoot_timer

    player_x = WIDTH / 2
    player_y = HEIGHT - 160
    lives = 3
    score = 0
    asteroids = []
    bullets = []
    spawn_timer = SPAWN_DELAY
    shoot_timer = 0


def spawn_asteroid():
    """Добавляет новый астероид за верхним краем экрана."""
    x = random.randint(70, WIDTH - 70)
    speed = random.randint(ASTEROID_SPEED[0], ASTEROID_SPEED[1])
    asteroids.append([x, -80, speed, 3])   # последнее число — сколько попаданий держит


def hit(x1, y1, r1, x2, y2, r2):
    """Проверяет, пересекаются ли два круга (упрощённое столкновение)."""
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy < (r1 + r2) ** 2


# ----------------------------------------------------------------------
#  Обновление игрового процесса
# ----------------------------------------------------------------------
def update_game(dt):
    """Сдвигает всё на экране на один кадр. dt — сколько секунд прошло."""
    global player_x, player_y, lives, score, asteroids, bullets
    global spawn_timer, shoot_timer, state

    # --- управление кораблём: WASD, ускорение на Space ---
    keys = pg.key.get_pressed()
    speed = BOOST_SPEED if keys[pg.K_SPACE] else PLAYER_SPEED
    if keys[pg.K_w]:
        player_y -= speed * dt
    if keys[pg.K_s]:
        player_y += speed * dt
    if keys[pg.K_a]:
        player_x -= speed * dt
    if keys[pg.K_d]:
        player_x += speed * dt

    # не даём кораблю улететь за край экрана
    player_x = max(40, min(player_x, WIDTH - 40))
    player_y = max(120, min(player_y, HEIGHT - 60))

    # --- стрельба левой кнопкой мыши ---
    shoot_timer -= dt
    if pg.mouse.get_pressed()[0] and shoot_timer <= 0:
        bullets.append([player_x, player_y - 62])
        shoot_timer = SHOOT_DELAY

    # --- полёт пуль ---
    for bullet in bullets:
        bullet[1] -= BULLET_SPEED * dt
    bullets = [bullet for bullet in bullets if bullet[1] > -40]

    # --- появление и полёт астероидов ---
    spawn_timer -= dt
    if spawn_timer <= 0:
        spawn_asteroid()
        spawn_timer = SPAWN_DELAY

    for asteroid in asteroids:
        asteroid[1] += asteroid[2] * dt
    asteroids = [a for a in asteroids if a[1] < HEIGHT + 100]

    # --- попадание пули в астероид: три попадания разрушают астероид ---
    for bullet in bullets[:]:
        for asteroid in asteroids[:]:
            if hit(bullet[0], bullet[1], 4, asteroid[0], asteroid[1], 28):
                bullets.remove(bullet)
                asteroid[3] -= 1          # попадание уменьшает прочность
                if asteroid[3] <= 0:
                    asteroids.remove(asteroid)
                    score += 10
                break

    # --- столкновение астероида с кораблём: минус одна жизнь ---
    for asteroid in asteroids[:]:
        if hit(player_x, player_y, 26, asteroid[0], asteroid[1], 28):
            asteroids.remove(asteroid)
            lives -= 1

    # жизни закончились — экран поражения
    if lives <= 0:
        lives = 0
        state = "over"


# ----------------------------------------------------------------------
#  Отрисовка
# ----------------------------------------------------------------------
def draw_hud():
    """Очки слева вверху, жизни справа вверху."""
    score_text = font_hud.render("Очки: " + str(score), True, WHITE)
    screen.blit(score_text, (26, 20))

    lives_text = font_hud.render("Жизни: " + str(lives), True, CYAN)
    screen.blit(lives_text, lives_text.get_rect(topright=(WIDTH - 26, 20)))


def draw_game():
    """Рисует фон, астероиды, пули, корабль и очки."""
    screen.blit(background, (0, 0))

    for asteroid in asteroids:
        # чем меньше прочность, тем сильнее повреждён астероид
        image = asteroid_images[3 - asteroid[3]]
        screen.blit(image, image.get_rect(center=(asteroid[0], asteroid[1])))

    for bullet in bullets:
        screen.blit(bullet_image, bullet_image.get_rect(center=(bullet[0], bullet[1])))

    # кадр корабля зависит от клавиш: ускорение, полёт или покой
    keys = pg.key.get_pressed()
    if keys[pg.K_SPACE]:
        ship = ship_boost
    elif any(keys[k] for k in (pg.K_w, pg.K_a, pg.K_s, pg.K_d)):
        ship = ship_fly
    else:
        ship = ship_idle
    screen.blit(ship, ship.get_rect(center=(player_x, player_y)))

    draw_hud()


def draw_button(text, rect):
    """Рисует кнопку и подсвечивает её, если курсор мыши наведён."""
    hover = rect.collidepoint(pg.mouse.get_pos())
    color = (38, 108, 168) if hover else (24, 66, 110)
    pg.draw.rect(screen, color, rect, border_radius=14)
    pg.draw.rect(screen, CYAN if hover else (60, 130, 180), rect, width=2, border_radius=14)
    label = font_button.render(text, True, WHITE)
    screen.blit(label, label.get_rect(center=rect.center))


def draw_overlay():
    """Тёмная полупрозрачная плёнка поверх игры для паузы и поражения."""
    overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    overlay.fill((4, 6, 16, 200))
    screen.blit(overlay, (0, 0))


def draw_menu():
    screen.blit(background, (0, 0))

    title = font_title.render("КОСМИЧЕСКИЕ ВОЙНЫ", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 280)))

    subtitle = font_big.render("ЛОЛОЛОШЕК", True, CYAN)
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 348)))

    draw_button("Играть", play_rect)


def draw_pause():
    draw_overlay()

    title = font_title.render("ПАУЗА", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 250)))

    draw_button("Продолжить", resume_rect)
    draw_button("В меню", pause_menu_rect)

    hint = font_small.render("Esc — продолжить,  Q — выход в меню", True, TEXT_DIM)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 530)))


def draw_game_over():
    draw_overlay()

    title = font_title.render("ИГРА ОКОНЧЕНА", True, RED)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 200)))

    subtitle = font_small.render(
        "Корабль уничтожен. В следующем заходе продержись дольше.",
        True,
        (200, 210, 230),
    )
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 256)))

    score_text = font_big.render("Очки: " + str(score), True, WHITE)
    screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, 320)))

    draw_button("Играть снова", again_rect)
    draw_button("В меню", finish_menu_rect)


# ----------------------------------------------------------------------
#  Главный цикл
# ----------------------------------------------------------------------
def main():
    global state

    running = True
    while running:
        # dt — время последнего кадра в секундах (не больше 0.05, чтобы игра не "прыгала")
        dt = min(clock.tick(FPS) / 1000, 0.05)
        events = pg.event.get()

        for event in events:
            if event.type == pg.QUIT:
                running = False

        # ---------------- МЕНЮ ----------------
        if state == "menu":
            for event in events:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_RETURN:
                        reset_game()
                        state = "playing"
                    elif event.key == pg.K_ESCAPE:
                        running = False
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    if play_rect.collidepoint(event.pos):
                        reset_game()
                        state = "playing"

            draw_menu()

        # ---------------- ИГРА ----------------
        elif state == "playing":
            for event in events:
                if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                    state = "paused"

            if state == "playing":
                update_game(dt)
                draw_game()

        # ---------------- ПАУЗА ----------------
        elif state == "paused":
            for event in events:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        state = "playing"
                    elif event.key == pg.K_q:
                        state = "menu"
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    if resume_rect.collidepoint(event.pos):
                        state = "playing"
                    elif pause_menu_rect.collidepoint(event.pos):
                        state = "menu"

            draw_game()
            draw_pause()

        # ---------------- ПОРАЖЕНИЕ ----------------
        else:
            for event in events:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_r or event.key == pg.K_RETURN:
                        reset_game()
                        state = "playing"
                    elif event.key == pg.K_ESCAPE:
                        state = "menu"
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    if again_rect.collidepoint(event.pos):
                        reset_game()
                        state = "playing"
                    elif finish_menu_rect.collidepoint(event.pos):
                        state = "menu"

            draw_game()
            draw_game_over()

        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()
