"""Космические войны лололошек — небольшая аркада на Pygame."""

import math
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

PLAYER_SPEED = 340
BOOST_SPEED = 560
BULLET_SPEED = 900
SHOOT_DELAY = 0.16

# бесконечный режим: пауза между астероидами сокращается с ростом очков
SPAWN_START = 1.0
SPAWN_MIN = 0.38
MAX_DIFFICULTY_SCORE = 900  # при таком счёте сложность максимальная

pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("Космические войны лололошек")
clock = pg.time.Clock()


# ----------------------------------------------------------------------
#  Картинки. Пути собираются от папки с main.py, поэтому игру можно
#  запускать из любого места.
# ----------------------------------------------------------------------
def load_image(folder, name, size):
    path = os.path.join(BASE_DIR, "assets", folder, name)
    image = pg.image.load(path).convert_alpha()
    return pg.transform.scale(image, size)


SHIP_SIZE = (64, 128)
ships_1 = [
    load_image("SpaceShip", "spaceship1.png", SHIP_SIZE),  # покой
    load_image("SpaceShip", "spaceship3.png", SHIP_SIZE),  # летит
    load_image("SpaceShip", "spaceship5.png", SHIP_SIZE),  # ускорение
]
ships_2 = [
    load_image("SpaceShip", "spaceship2.png", SHIP_SIZE),
    load_image("SpaceShip", "spaceship4.png", SHIP_SIZE),
    load_image("SpaceShip", "spaceship6.png", SHIP_SIZE),
]

ASTEROID_SIZE = (64, 64)
asteroid_images = [
    load_image("Asteroid", "Asteroid1.png", ASTEROID_SIZE),  # целый
    load_image("Asteroid", "Asteroid2.png", ASTEROID_SIZE),  # треснутый
    load_image("Asteroid", "Asteroid3.png", ASTEROID_SIZE),  # обломки
]

bullet_yellow = load_image("Bull", "bull1.png", (14, 30))
bullet_blue = load_image("Bull", "bull2.png", (14, 30))


# ----------------------------------------------------------------------
#  Шрифты
# ----------------------------------------------------------------------
def make_font(size, bold=False):
    return pg.font.SysFont("arial", size, bold=bold)


font_title = make_font(64, True)
font_big = make_font(42, True)
font_hud = make_font(26, True)
font_button = make_font(30, True)
font_small = make_font(20)


# ----------------------------------------------------------------------
#  Фон: тёмный космос и падающие звёзды
# ----------------------------------------------------------------------
def make_stars():
    stars = []
    for i in range(180):
        speed = random.choice([25, 45, 80])
        size = 1 if speed == 25 else (2 if speed == 45 else 3)
        stars.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), speed, size])
    return stars


def update_stars(dt):
    for star in stars:
        star[1] += star[2] * dt
        if star[1] > HEIGHT:
            star[1] = -2
            star[0] = random.randint(0, WIDTH)


background = pg.Surface((WIDTH, HEIGHT)).convert()
background.fill((6, 7, 20))
stars = make_stars()


# ----------------------------------------------------------------------
#  Состояние игры
# ----------------------------------------------------------------------
state = "menu"

player_x = WIDTH / 2
player_y = HEIGHT - 160
lives = 3
score = 0

asteroids = []
bullets = []
particles = []

spawn_timer = 0.8
shoot_timer = 0.0
invuln_timer = 0.0
flash_timer = 0.0

play_rect = pg.Rect(WIDTH // 2 - 170, 410, 340, 66)

resume_rect = pg.Rect(WIDTH // 2 - 170, 360, 340, 64)
pause_menu_rect = pg.Rect(WIDTH // 2 - 170, 442, 340, 64)

again_rect = pg.Rect(WIDTH // 2 - 170, 430, 340, 64)
finish_menu_rect = pg.Rect(WIDTH // 2 - 170, 512, 340, 64)


def reset_game():
    """Возвращает все переменные в начальное состояние."""
    global player_x, player_y, lives, score
    global asteroids, bullets, particles
    global spawn_timer, shoot_timer, invuln_timer, flash_timer

    player_x = WIDTH / 2
    player_y = HEIGHT - 160
    lives = 3
    score = 0
    asteroids = []
    bullets = []
    particles = []
    spawn_timer = 0.8
    shoot_timer = 0.0
    invuln_timer = 0.0
    flash_timer = 0.0


def difficulty():
    """Чем больше очков, тем чаще и быстрее летят астероиды."""
    return min(1.0, score / MAX_DIFFICULTY_SCORE)


def improved_ship():
    """С 70 очков корабль выглядит мощнее и стреляет синими зарядами."""
    return score >= 70


def spawn_asteroid():
    asteroids.append({
        "x": random.randint(70, WIDTH - 70),
        "y": -80,
        "hp": 3,
        "speed": random.uniform(70, 110) * (1 + 0.9 * difficulty()),
        "angle": random.uniform(0, 360),
        "spin": random.uniform(-45, 45),
    })


def shoot():
    global shoot_timer
    bullets.append([player_x, player_y - 62])
    shoot_timer = SHOOT_DELAY


def explode(x, y, count, color):
    for i in range(count):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(40, 260)
        life = random.uniform(0.3, 0.8)
        particles.append({
            "x": x,
            "y": y,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "life": life,
            "full": life,
            "size": random.choice([2, 3, 4]),
            "color": color,
        })


def circles_hit(x1, y1, r1, x2, y2, r2):
    """Проверка столкновения двух кругов."""
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy < (r1 + r2) ** 2


def finish_game():
    global state
    state = "over"


def player_image():
    """Кадр корабля зависит от нажатых клавиш и счёта."""
    keys = pg.key.get_pressed()
    ship_set = ships_2 if improved_ship() else ships_1

    if keys[pg.K_SPACE]:
        return ship_set[2]
    if keys[pg.K_w] or keys[pg.K_s] or keys[pg.K_a] or keys[pg.K_d]:
        return ship_set[1]
    return ship_set[0]


# ----------------------------------------------------------------------
#  Обновление игрового процесса
# ----------------------------------------------------------------------
def update_playing(dt):
    global player_x, player_y, lives, score
    global bullets, asteroids, particles, spawn_timer, shoot_timer
    global invuln_timer, flash_timer

    keys = pg.key.get_pressed()
    current_speed = BOOST_SPEED if keys[pg.K_SPACE] else PLAYER_SPEED

    if keys[pg.K_w]:
        player_y -= current_speed * dt
    if keys[pg.K_s]:
        player_y += current_speed * dt
    if keys[pg.K_a]:
        player_x -= current_speed * dt
    if keys[pg.K_d]:
        player_x += current_speed * dt

    player_x = max(40, min(player_x, WIDTH - 40))
    player_y = max(120, min(player_y, HEIGHT - 60))

    # стрельба
    shoot_timer -= dt
    if pg.mouse.get_pressed()[0] and shoot_timer <= 0:
        shoot()

    for bullet in bullets:
        bullet[1] -= BULLET_SPEED * dt
    bullets = [bullet for bullet in bullets if bullet[1] > -40]

    # астероиды летят всё время, пауза между ними сокращается со счётом
    spawn_timer -= dt
    if spawn_timer <= 0:
        spawn_asteroid()
        spawn_timer = SPAWN_START - (SPAWN_START - SPAWN_MIN) * difficulty()

    for asteroid in asteroids:
        asteroid["y"] += asteroid["speed"] * dt
        asteroid["angle"] += asteroid["spin"] * dt
    asteroids = [asteroid for asteroid in asteroids if asteroid["y"] < HEIGHT + 100]

    # попадания пуль по астероидам
    for bullet in bullets[:]:
        for asteroid in asteroids[:]:
            if circles_hit(bullet[0], bullet[1], 4, asteroid["x"], asteroid["y"], 28):
                bullets.remove(bullet)
                asteroid["hp"] -= 1
                if asteroid["hp"] <= 0:
                    asteroids.remove(asteroid)
                    explode(asteroid["x"], asteroid["y"], 20, (255, 175, 70))
                    score += 10
                else:
                    explode(asteroid["x"], asteroid["y"], 6, (205, 210, 225))
                break

    # столкновение астероида с кораблём
    if invuln_timer > 0:
        invuln_timer -= dt

    for asteroid in asteroids[:]:
        if circles_hit(player_x, player_y, 26, asteroid["x"], asteroid["y"], 28):
            if invuln_timer <= 0:
                lives -= 1
                invuln_timer = 2.0
                flash_timer = 0.35
                explode(player_x, player_y, 26, (110, 220, 255))
                asteroids.remove(asteroid)
                if lives <= 0:
                    finish_game()
                    return

    # частицы
    for particle in particles:
        particle["x"] += particle["vx"] * dt
        particle["y"] += particle["vy"] * dt
        particle["vx"] *= 0.98
        particle["vy"] *= 0.98
        particle["life"] -= dt
    particles = [particle for particle in particles if particle["life"] > 0]

    if flash_timer > 0:
        flash_timer -= dt


# ----------------------------------------------------------------------
#  Отрисовка
# ----------------------------------------------------------------------
def draw_background():
    screen.blit(background, (0, 0))
    for star in stars:
        x, y, speed, size = star
        brightness = 90 + size * 55
        color = (brightness, brightness, min(255, brightness + 40))
        pg.draw.circle(screen, color, (int(x), int(y)), size)


def draw_world():
    for asteroid in asteroids:
        image = pg.transform.rotate(asteroid_images[3 - asteroid["hp"]], asteroid["angle"])
        screen.blit(image, image.get_rect(center=(asteroid["x"], asteroid["y"])))

    bullet_image = bullet_blue if improved_ship() else bullet_yellow
    for bullet in bullets:
        screen.blit(bullet_image, bullet_image.get_rect(center=(bullet[0], bullet[1])))

    for particle in particles:
        fade = max(0.0, min(1.0, particle["life"] / particle["full"]))
        color = (
            int(particle["color"][0] * fade),
            int(particle["color"][1] * fade),
            int(particle["color"][2] * fade),
        )
        size = particle["size"]
        pg.draw.rect(screen, color, (int(particle["x"]), int(particle["y"]), size, size))

    if invuln_timer <= 0 or int(invuln_timer * 12) % 2 == 0:
        ship = player_image()
        screen.blit(ship, ship.get_rect(center=(player_x, player_y)))


def draw_hud():
    score_text = font_hud.render("Очки: " + str(score), True, WHITE)
    screen.blit(score_text, (26, 20))

    lives_text = font_hud.render("Жизни: " + str(lives), True, CYAN)
    screen.blit(lives_text, lives_text.get_rect(topright=(WIDTH - 26, 20)))

    if flash_timer > 0:
        flash = pg.Surface((WIDTH, HEIGHT))
        flash.fill((110, 0, 0))
        flash.set_alpha(int(150 * flash_timer / 0.35))
        screen.blit(flash, (0, 0))


def draw_button(text, rect, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (38, 108, 168) if hover else (24, 66, 110)
    pg.draw.rect(screen, color, rect, border_radius=14)
    pg.draw.rect(screen, CYAN if hover else (60, 130, 180), rect, width=2, border_radius=14)
    label = font_button.render(text, True, WHITE)
    screen.blit(label, label.get_rect(center=rect.center))


def draw_dark_overlay():
    overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    overlay.fill((4, 6, 16, 200))
    screen.blit(overlay, (0, 0))


def draw_menu(mouse_pos):
    title = font_title.render("КОСМИЧЕСКИЕ ВОЙНЫ", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 280)))

    subtitle = font_big.render("ЛОЛОЛОШЕК", True, CYAN)
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 348)))

    draw_button("Играть", play_rect, mouse_pos)


def draw_pause(mouse_pos):
    draw_dark_overlay()
    title = font_title.render("ПАУЗА", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 250)))

    draw_button("Продолжить", resume_rect, mouse_pos)
    draw_button("В меню", pause_menu_rect, mouse_pos)

    hint = font_small.render("Esc — продолжить,  Q — выход в меню", True, TEXT_DIM)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 530)))


def draw_finish(mouse_pos):
    draw_dark_overlay()

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

    draw_button("Играть снова", again_rect, mouse_pos)
    draw_button("В меню", finish_menu_rect, mouse_pos)


# ----------------------------------------------------------------------
#  Главный цикл
# ----------------------------------------------------------------------
def main():
    global state

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        events = pg.event.get()
        mouse_pos = pg.mouse.get_pos()

        for event in events:
            if event.type == pg.QUIT:
                running = False

        update_stars(dt)

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

            draw_background()
            draw_menu(mouse_pos)

        else:
            if state == "playing":
                for event in events:
                    if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                        state = "paused"
                if state == "playing":
                    update_playing(dt)

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

            else:  # "over"
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

            draw_background()
            draw_world()
            draw_hud()

            if state == "paused":
                draw_pause(mouse_pos)
            elif state == "over":
                draw_finish(mouse_pos)

        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()
