import os
import random
import math
import pygame
from os import listdir
from os.path import isfile, join

pygame.init()
pygame.font.init()

pygame.display.set_caption("Platformer")

WIDTH, HEIGHT = 1000, 800
FPS = 60
PLAYER_VEL = 5

window = pygame.display.set_mode((WIDTH, HEIGHT))

font_large  = pygame.font.Font('never.ttf', 72)
font_medium = pygame.font.Font('never.ttf', 48)
font_small  = pygame.font.Font('never.ttf', 28)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}
    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()
        sprites = []
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites


def get_block(size):
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    rect = pygame.Rect(96, 0, size, size)
    surface.blit(image, (0, 0), rect)
    return pygame.transform.scale2x(surface)


def get_background(name):
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []
    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            tiles.append([i * width, j * height])
    return tiles, image


def draw_text(surface, text, color, x, y, font=None):
    f = font or font_medium
    text_surface = f.render(text, True, color)
    surface.blit(text_surface, (x, y))


def draw_text_centered(surface, text, color, cx, y, font=None):
    f = font or font_medium
    text_surface = f.render(text, True, color)
    surface.blit(text_surface, (cx - text_surface.get_width() // 2, y))


# ---------------------------------------------------------------------------
# Sprite / Object classes
# ---------------------------------------------------------------------------

class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    def draw(self, win, offset_x):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        block = get_block(size)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, name="fire")
        self.fire = load_sprite_sheets("Traps", "Fire", width, height)
        self.image = self.fire["off"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name = "off"

    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    def loop(self):
        sprites = self.fire[self.animation_name]
        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1
        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)
        if self.animation_count >= self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height, sprite_name="NinjaFrog"):
        super().__init__()
        self.start_x = x
        self.start_y = y
        self.sprite_name = sprite_name
        # Sprites are per-instance so each player can use a different character
        self.SPRITES = load_sprite_sheets("MainCharacters", sprite_name, 32, 32, True)
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.health = 100
        # Bootstrap sprite so draw() is safe before the first loop()
        self.sprite = self.SPRITES["idle_left"][0]
        self.update()

    # -- movement --

    def jump(self):
        self.y_vel = -self.GRAVITY * 12
        self.animation_count = 0
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    # -- state --

    def make_hit(self):
        self.hit = True
        self.hit_count = 0
        self.health -= 10

    def landed(self):
        self.y_vel = 0
        self.fall_count = 0
        self.jump_count = 0

    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    def reset(self):
        """Return the player to its starting position and full health."""
        self.rect.x = self.start_x
        self.rect.y = self.start_y
        self.x_vel = 0
        self.y_vel = 0
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.health = 100

    # -- per-frame logic --

    def loop(self, fps):
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)

        if self.hit:
            self.hit_count += 1
        if self.hit_count > FPS / 2:
            self.hit = False
            self.hit_count = 0

        self.fall_count += 1
        self.update_sprite()

    def update_sprite(self):
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            sprite_sheet = "jump" if self.jump_count == 1 else "double_jump"
        elif self.y_vel >= self.GRAVITY * 2:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        sprites = self.SPRITES[sprite_sheet + "_" + self.direction]
        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        self.update()

    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))


# ---------------------------------------------------------------------------
# Collision helpers
# ---------------------------------------------------------------------------

def handle_vertical_collision(player, objects, dy):
    collided_objects = []
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()
            collided_objects.append(obj)
    return collided_objects


def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            collided_object = obj
            break
    player.move(-dx, 0)
    player.update()
    return collided_object


def handle_move(player, objects):
    keys = pygame.key.get_pressed()
    player.x_vel = 0

    collide_left = collide(player, objects, -PLAYER_VEL * 2)
    collide_right = collide(player, objects, PLAYER_VEL * 2)

    if keys[pygame.K_LEFT] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not collide_right:
        player.move_right(PLAYER_VEL)

    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    for obj in [collide_left, collide_right, *vertical_collide]:
        if obj and obj.name == "fire":
            player.make_hit()

    if player.rect.top > HEIGHT:
        player.health = 0


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

# Pixel-art colour palette
COL_BG_DARK    = (10,  14,  30)
COL_CARD_IDLE  = (25,  32,  60)
COL_CARD_SEL   = (35,  50, 100)
COL_BORDER_SEL = (255, 210,  50)
COL_BORDER_IDL = (60,  70, 120)
COL_TITLE      = (255, 230,  80)
COL_WHITE      = (240, 240, 255)
COL_DIM        = (130, 140, 170)
COL_BTN_FACE   = (50, 160,  90)
COL_BTN_HOV    = (70, 210, 110)
COL_BTN_TEXT   = (10,  30,  15)

AVAILABLE_CHARACTERS = ["NinjaFrog", "PinkMan"]


class Particle:
    """Tiny floating star for the menu background."""
    def __init__(self):
        self.reset(born=False)

    def reset(self, born=True):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT) if not born else HEIGHT + 5
        self.speed = random.uniform(0.3, 1.0)
        self.size  = random.randint(1, 3)
        self.alpha = random.randint(80, 220)

    def update(self):
        self.y -= self.speed
        if self.y < -4:
            self.reset()

    def draw(self, surface):
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*COL_WHITE[:3], self.alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


class CharacterCard:
    """
    An animated preview card for one playable character.
    Shows a looping idle animation, the character name, and a selection border.
    """
    ANIM_DELAY    = 6
    PREVIEW_SCALE = 5

    def __init__(self, sprite_name: str, cx: int, cy: int):
        self.sprite_name = sprite_name
        self.cx = cx
        self.cy = cy
        self.card_w = 220
        self.card_h = 280

        sheets = load_sprite_sheets("MainCharacters", sprite_name, 32, 32, True)
        raw_frames = sheets["idle_right"]
        self.frames = [
            pygame.transform.scale(
                f,
                (f.get_width()  * self.PREVIEW_SCALE // 2,
                 f.get_height() * self.PREVIEW_SCALE // 2)
            )
            for f in raw_frames
        ]
        self.anim_count = 0

        self._card_rect = pygame.Rect(
            cx - self.card_w // 2,
            cy - self.card_h // 2,
            self.card_w,
            self.card_h,
        )

    @property
    def _current_frame(self):
        idx = (self.anim_count // self.ANIM_DELAY) % len(self.frames)
        return self.frames[idx]

    def update(self):
        self.anim_count += 1

    def draw(self, surface, selected: bool):
        border_col = COL_BORDER_SEL if selected else COL_BORDER_IDL
        face_col   = COL_CARD_SEL   if selected else COL_CARD_IDLE
        border_w   = 4              if selected else 2

        # Shadow
        shadow = pygame.Surface((self.card_w + 8, self.card_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 80), shadow.get_rect(), border_radius=16)
        surface.blit(shadow, (self._card_rect.x - 4, self._card_rect.y + 6))

        # Card face + border
        pygame.draw.rect(surface, face_col, self._card_rect, border_radius=14)
        pygame.draw.rect(surface, border_col, self._card_rect, border_w, border_radius=14)

        # Animated sprite centred in upper card area
        frame = self._current_frame
        fw, fh = frame.get_size()
        fx = self.cx - fw // 2
        fy = self._card_rect.y + 30
        surface.blit(frame, (fx, fy))

        # Character name
        label = font_small.render(self.sprite_name, True,
                                  COL_WHITE if selected else COL_DIM)
        surface.blit(label, (self.cx - label.get_width() // 2,
                              self._card_rect.bottom - 52))

        # "selected" badge
        if selected:
            hint = font_small.render("selected", True, COL_BORDER_SEL)
            surface.blit(hint, (self.cx - hint.get_width() // 2,
                                 self._card_rect.bottom - 24))

    def is_hovered(self, mx, my):
        return self._card_rect.collidepoint(mx, my)


class Menu:
    """
    Full-screen main menu.

    Navigation:
      LEFT / RIGHT arrow keys  — cycle character selection
      ENTER or SPACE           — confirm and start
      Click a card             — select it; click it again to start
      Click "START GAME"       — start with current selection
    """

    def __init__(self, window: pygame.Surface):
        self.window  = window
        self.clock   = pygame.time.Clock()
        self.running = True
        self.selected_index = 0

        self.bg_tiles, self.bg_image = get_background("Blue.png")

        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((5, 8, 20, 185))

        self.particles = [Particle() for _ in range(60)]

        spacing = 240
        self.cards = [
            CharacterCard(AVAILABLE_CHARACTERS[0], WIDTH // 2 - spacing, HEIGHT // 2 - 10),
            CharacterCard(AVAILABLE_CHARACTERS[1], WIDTH // 2 + spacing, HEIGHT // 2 - 10),
        ]

        btn_w, btn_h = 280, 64
        self._btn_rect = pygame.Rect(WIDTH // 2 - btn_w // 2,
                                     HEIGHT // 2 + 190,
                                     btn_w, btn_h)
        self._title_t = 0.0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> str:
        """Block until the player confirms a character. Returns sprite_name."""
        self.running = True
        while self.running:
            self.clock.tick(FPS)
            result = self._handle_events()
            if result:
                return result
            self._update()
            self._draw()
        return AVAILABLE_CHARACTERS[self.selected_index]

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _handle_events(self):
        mx, my = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_index = (self.selected_index - 1) % len(self.cards)
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_index = (self.selected_index + 1) % len(self.cards)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return AVAILABLE_CHARACTERS[self.selected_index]

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, card in enumerate(self.cards):
                    if card.is_hovered(mx, my):
                        if self.selected_index == i:
                            return AVAILABLE_CHARACTERS[self.selected_index]
                        self.selected_index = i
                if self._btn_rect.collidepoint(mx, my):
                    return AVAILABLE_CHARACTERS[self.selected_index]
        return None

    def _update(self):
        for p in self.particles:
            p.update()
        for card in self.cards:
            card.update()
        self._title_t += 0.04

    def _draw(self):
        for tile in self.bg_tiles:
            self.window.blit(self.bg_image, tile)
        self.window.blit(self.overlay, (0, 0))
        for p in self.particles:
            p.draw(self.window)

        # Pulsing title
        pulse = 1.0 + 0.025 * math.sin(self._title_t)
        title_surf = font_large.render("PLATFORMER", True, COL_TITLE)
        tw = int(title_surf.get_width()  * pulse)
        th = int(title_surf.get_height() * pulse)
        title_scaled = pygame.transform.smoothscale(title_surf, (tw, th))
        self.window.blit(title_scaled, (WIDTH // 2 - tw // 2, 60))

        draw_text_centered(self.window, "Choose your character",
                            COL_DIM, WIDTH // 2, 155, font_small)

        for i, card in enumerate(self.cards):
            card.draw(self.window, selected=(i == self.selected_index))

        draw_text_centered(self.window, "◀  ▶  arrow keys to navigate",
                            COL_DIM, WIDTH // 2, HEIGHT // 2 + 165, font_small)

        # Start button
        mx, my = pygame.mouse.get_pos()
        btn_color = COL_BTN_HOV if self._btn_rect.collidepoint(mx, my) else COL_BTN_FACE

        shadow_r = self._btn_rect.inflate(6, 6).move(3, 4)
        shadow_s = pygame.Surface(shadow_r.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow_s, (0, 0, 0, 70), shadow_s.get_rect(), border_radius=14)
        self.window.blit(shadow_s, shadow_r.topleft)

        pygame.draw.rect(self.window, btn_color, self._btn_rect, border_radius=12)
        pygame.draw.rect(self.window, COL_WHITE,  self._btn_rect, 2, border_radius=12)

        btn_label = font_small.render("▶  START GAME", True, COL_BTN_TEXT)
        self.window.blit(btn_label, (
            self._btn_rect.centerx - btn_label.get_width()  // 2,
            self._btn_rect.centery - btn_label.get_height() // 2,
        ))

        pygame.display.update()


# ---------------------------------------------------------------------------
# Game  (owns the loop, all objects, and all state)
# ---------------------------------------------------------------------------

class Game:
    BLOCK_SIZE = 96
    SCROLL_AREA_WIDTH = 200

    def __init__(self, window: pygame.Surface, sprite_name: str = "NinjaFrog"):
        self.window      = window
        self.clock       = pygame.time.Clock()
        self.sprite_name = sprite_name

        self.score   = 0
        self.level   = 1
        self.running = False

        self.background, self.bg_image = get_background("Blue.png")
        self._build_scene()

    # ------------------------------------------------------------------
    # Scene construction
    # ------------------------------------------------------------------

    def _build_scene(self):
        bs = self.BLOCK_SIZE

        self.player = Player(100, 100, 50, 50, sprite_name=self.sprite_name)

        self.fire = Fire(100, HEIGHT - bs - 64, 16, 32)
        self.fire.on()

        floor = [
            Block(i * bs, HEIGHT - bs, bs)
            for i in range(-WIDTH // bs, WIDTH * 2 // bs)
        ]
        self.objects = [
            *floor,
            Block(0,       HEIGHT - bs * 2, bs),
            Block(bs * 5,  HEIGHT - bs * 2, bs),
            Block(bs * 3,  HEIGHT - bs * 4, bs),
            self.fire,
        ]
        self.offset_x = 0

    def _scene_generator(self):
        bs = self.BLOCK_SIZE
        block_level = self.level
        bs = self.BLOCK_SIZE
        for i in range(1, block_level):
            self.objects.append(Block(bs * 2, bs * i, bs))


    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self):
        """Start the main game loop. Returns when the game ends."""
        self.running = True
        self._loop()

    def restart(self):
        self.score = 0
        self.level = 1
        self.player.reset()
        self.offset_x = 0
        self.run()

    def level_up(self):
        self.level += 1
        self.score += 100

    # ------------------------------------------------------------------
    # Private — per-frame logic
    # ------------------------------------------------------------------

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and self.player.jump_count < 2:
                    self.player.jump()
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def _update(self):
        self.player.loop(FPS)
        self.fire.loop()
        handle_move(self.player, self.objects)

        if self.player.health <= 0:
            self.running = False

        p = self.player
        if (p.rect.right - self.offset_x >= WIDTH - self.SCROLL_AREA_WIDTH and p.x_vel > 0) or \
           (p.rect.left  - self.offset_x <= self.SCROLL_AREA_WIDTH          and p.x_vel < 0):
            self.offset_x += p.x_vel

    def _draw(self):
        for tile in self.background:
            self.window.blit(self.bg_image, tile)
        for obj in self.objects:
            obj.draw(self.window, self.offset_x)
        self.player.draw(self.window, self.offset_x)

        draw_text(self.window, f"HP: {self.player.health}", (0, 0, 0), 20, 20)
        draw_text(self.window, f"Score: {self.score}",       (0, 0, 0), 20, 70)
        draw_text(self.window, f"Level: {self.level}",       (0, 0, 0), 20, 120)

        hint = font_small.render("ESC — menu", True, (80, 80, 80))
        self.window.blit(hint, (WIDTH - hint.get_width() - 16, 20))

        pygame.display.update()

    def _loop(self):
        while self.running:
            self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()


# ---------------------------------------------------------------------------
# Entry point — menu → game → menu loop
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    menu = Menu(window)

    while True:
        chosen_sprite = menu.run()      # blocks until player starts
        game = Game(window, chosen_sprite)
        game.run()                      # blocks until player dies or ESCs
        # After game ends, loop back to the menu