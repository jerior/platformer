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
LEVEL_SCREENS = 10   # level world width = LEVEL_SCREENS × viewport width

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
    """Returns just the single tile image; drawing is handled dynamically."""
    return pygame.image.load(join("assets", "Background", name))


def draw_text(surface, text, color, x, y, font=None):
    f = font or font_medium
    surface.blit(f.render(text, True, color), (x, y))


def draw_text_centered(surface, text, color, cx, y, font=None):
    f = font or font_medium
    surf = f.render(text, True, color)
    surface.blit(surf, (cx - surf.get_width() // 2, y))


# ---------------------------------------------------------------------------
# Object / Sprite classes
# ---------------------------------------------------------------------------

class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect  = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width, self.height, self.name = width, height, name

    def draw(self, win, offset_x):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        self.image.blit(get_block(size), (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, name="fire")
        self.fire = load_sprite_sheets("Traps", "Fire", width, height)
        self.image = self.fire["off"][0]
        self.mask  = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name  = "off"

    def on(self):  self.animation_name = "on"
    def off(self): self.animation_name = "off"

    def loop(self):
        sprites = self.fire[self.animation_name]
        idx = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[idx]
        self.animation_count += 1
        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)
        if self.animation_count >= self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0


class GoalPost(Object):
    """
    Purely visual flag-pole that marks the end of a level.
    Collision is detected positionally in Game._update().
    """
    POLE_W  = 14
    FLAG_W  = 48
    FLAG_H  = 34

    def __init__(self, x: int, block_size: int):
        pole_h  = block_size * 5
        total_w = self.POLE_W + self.FLAG_W + 6
        px      = x + block_size // 2 - self.POLE_W // 2
        py      = HEIGHT - block_size - pole_h
        super().__init__(px, py, total_w, pole_h, name="goal")

        surf = pygame.Surface((total_w, pole_h), pygame.SRCALPHA)

        # Gold pole
        pygame.draw.rect(surf, (255, 215,  0), (0, 0, self.POLE_W, pole_h), border_radius=4)
        pygame.draw.rect(surf, (200, 160,  0), (0, 0, self.POLE_W, pole_h), 2, border_radius=4)

        # Triangular green flag at the top
        pts = [
            (self.POLE_W + 3, 6),
            (self.POLE_W + 3 + self.FLAG_W, 6 + self.FLAG_H // 2),
            (self.POLE_W + 3, 6 + self.FLAG_H),
        ]
        pygame.draw.polygon(surf, ( 50, 210,  80), pts)
        pygame.draw.polygon(surf, ( 20, 150,  40), pts, 2)

        # Small star on the flag
        cx = self.POLE_W + 3 + self.FLAG_W // 3
        cy = 6 + self.FLAG_H // 2
        for angle in range(0, 360, 72):
            ax = cx + int(10 * math.cos(math.radians(angle - 90)))
            ay = cy + int(10 * math.sin(math.radians(angle - 90)))
            bx = cx + int( 4 * math.cos(math.radians(angle - 90 + 36)))
            by = cy + int( 4 * math.sin(math.radians(angle - 90 + 36)))
            pygame.draw.line(surf, (255, 255, 150), (cx, cy), (ax, ay), 2)
            pygame.draw.line(surf, (255, 255, 150), (cx, cy), (bx, by), 1)

        self.image = surf
        self.mask  = pygame.mask.from_surface(self.image)


class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height, sprite_name="NinjaFrog"):
        super().__init__()
        self.start_x, self.start_y = x, y
        self.sprite_name = sprite_name
        self.SPRITES = load_sprite_sheets("MainCharacters", sprite_name, 32, 32, True)
        self.rect    = pygame.Rect(x, y, width, height)
        self.x_vel = self.y_vel = 0
        self.mask   = None
        self.direction = "left"
        self.animation_count = self.fall_count = self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.health = 100
        self.sprite = self.SPRITES["idle_left"][0]
        self.update()

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

    def make_hit(self):
        self.hit = True
        self.hit_count = 0
        self.health -= 10

    def landed(self):
        self.y_vel = self.fall_count = self.jump_count = 0

    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    def reset(self, health=100):
        self.rect.x, self.rect.y = self.start_x, self.start_y
        self.x_vel = self.y_vel = 0
        self.direction = "left"
        self.animation_count = self.fall_count = self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.health = health

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
        sheet = "idle"
        if self.hit:
            sheet = "hit"
        elif self.y_vel < 0:
            sheet = "jump" if self.jump_count == 1 else "double_jump"
        elif self.y_vel >= self.GRAVITY * 2:
            sheet = "fall"
        elif self.x_vel != 0:
            sheet = "run"
        sprites = self.SPRITES[sheet + "_" + self.direction]
        self.sprite = sprites[(self.animation_count // self.ANIMATION_DELAY) % len(sprites)]
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
    collided = []
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()
            collided.append(obj)
    return collided


def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    hit = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            hit = obj
            break
    player.move(-dx, 0)
    player.update()
    return hit


def handle_move(player, objects):
    keys = pygame.key.get_pressed()
    player.x_vel = 0
    cl = collide(player, objects, -PLAYER_VEL * 2)
    cr = collide(player, objects, +PLAYER_VEL * 2)
    if keys[pygame.K_LEFT]  and not cl: player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not cr: player.move_right(PLAYER_VEL)
    vc = handle_vertical_collision(player, objects, player.y_vel)
    for obj in [cl, cr, *vc]:
        if obj and obj.name == "fire":
            player.make_hit()
    if player.rect.top > HEIGHT:
        player.health = 0


# ---------------------------------------------------------------------------
# Level generator
# ---------------------------------------------------------------------------

def generate_level(level_num: int, block_size: int) -> dict:
    """
    Procedurally generate a level that is LEVEL_SCREENS viewports wide.

    Layout rules:
      - Floor has random gaps; long gaps (>=2 blocks) always get a
        floating platform bridge so the player can cross them.
      - Fire is placed on solid floor sections away from gap edges.
      - A few extra decorative platforms are scattered for variety.
      - Goal post sits at the far end.

    Returns a dict with:
      floor_blocks    – Block list (floor row, with holes)
      platform_blocks – Block list (floating platforms)
      fires           – Fire list
      goal            – GoalPost object
      level_width     – int, total pixel width of the level
      all_objects     – flat list of every collidable object (for collision)
    """
    bs         = block_size
    total_cols = (WIDTH * LEVEL_SCREENS) // bs
    level_width = total_cols * bs

    # ------------------------------------------------------------------ #
    # Difficulty: scales gently with level number                         #
    # ------------------------------------------------------------------ #
    hole_chance = min(0.18 + level_num * 0.03, 0.40)   # chance to start a gap
    max_hole_w  = min(2 + (level_num - 1) // 2, 4)     # max gap width (grows over levels)
    fire_chance = min(0.08 + level_num * 0.03, 0.28)   # fire per eligible floor column

    SAFE_START = 4   # solid columns guaranteed at the start
    SAFE_END   = 4   # solid columns guaranteed at the end

    # ------------------------------------------------------------------ #
    # 1. Floor — walk left→right and punch gaps                           #
    # ------------------------------------------------------------------ #
    solid_cols: set[int] = set()

    for c in range(SAFE_START):
        solid_cols.add(c)
    for c in range(total_cols - SAFE_END, total_cols):
        solid_cols.add(c)

    col       = SAFE_START
    solid_run = SAFE_START

    while col < total_cols - SAFE_END:
        if solid_run >= 3 and random.random() < hole_chance:
            hole_w = random.randint(2, max_hole_w)          # minimum gap = 2 so a platform is always needed
            hole_w = min(hole_w, total_cols - SAFE_END - col - 1)
            col       += hole_w   # skip these columns — they become the gap
            solid_run  = 0
        else:
            solid_cols.add(col)
            col       += 1
            solid_run += 1

    floor_blocks = [Block(c * bs, HEIGHT - bs, bs) for c in sorted(solid_cols)]

    # ------------------------------------------------------------------ #
    # 2. Find every gap and its width                                     #
    # ------------------------------------------------------------------ #
    gaps: list[tuple[int, int]] = []   # (start_col, gap_width)
    sorted_all = list(range(total_cols))
    in_gap     = False
    gap_start  = 0

    for c in sorted_all:
        if c not in solid_cols:
            if not in_gap:
                gap_start = c
                in_gap    = True
        else:
            if in_gap:
                gaps.append((gap_start, c - gap_start))
                in_gap = False
    if in_gap:
        gaps.append((gap_start, total_cols - gap_start))

    # ------------------------------------------------------------------ #
    # 3. Platforms — one bridge over every gap + a few random extras      #
    # ------------------------------------------------------------------ #
    platform_blocks: list[Block] = []
    occupied_cols: set[int] = set()   # tracks columns already used by a platform

    def add_platform(start_col: int, width: int, height_blocks: int):
        """Place `width` blocks starting at start_col, height_blocks above floor."""
        plat_y = HEIGHT - bs - height_blocks * bs
        for pc in range(width):
            cx = start_col + pc
            platform_blocks.append(Block(cx * bs, plat_y, bs))
            occupied_cols.add(cx)

    # Bridge every gap: centre a 2-block-wide platform above it,
    # high enough to be reachable with a single or double jump (2-3 blocks up).
    for gap_start, gap_w in gaps:
        if gap_w < 2:
            continue  # single-block gaps are trivially jumpable
        bridge_w    = min(gap_w, 3)                        # 2–3 wide
        bridge_col  = gap_start + (gap_w - bridge_w) // 2 # centred in the gap
        height_up   = random.randint(2, 3)                 # 2 or 3 blocks above floor
        add_platform(bridge_col, bridge_w, height_up)

    # Scatter a few extra decorative platforms for variety
    c = SAFE_START + 2
    while c < total_cols - SAFE_END - 4:
        if c not in occupied_cols and random.random() < 0.30:
            plat_w  = random.randint(1, 3)
            plat_h  = random.randint(2, 4)
            # Only place if there is solid floor nearby (reachable from the side)
            if any(cc in solid_cols for cc in range(c - 1, c + plat_w + 2)):
                add_platform(c, plat_w, plat_h)
                c += plat_w + random.randint(3, 6)
                continue
        c += 1

    # ------------------------------------------------------------------ #
    # 4. Fire — only on solid floor, at least 1 block from any gap edge   #
    # ------------------------------------------------------------------ #
    fires: list[Fire] = []

    for c in sorted(solid_cols):
        if c < SAFE_START + 1 or c >= total_cols - SAFE_END - 1:
            continue
        # Skip columns adjacent to a gap (player is mid-jump there)
        if (c - 1) not in solid_cols or (c + 1) not in solid_cols:
            continue
        if random.random() < fire_chance:
            fire_x = c * bs + (bs - 32) // 2   # centre 32-px sprite in 96-px block
            fire_y = HEIGHT - bs - 64           # 64 = rendered fire height after scale2x
            f = Fire(fire_x, fire_y, 16, 32)
            f.on()
            fires.append(f)

    # ------------------------------------------------------------------ #
    # 5. Goal post at the far end                                         #
    # ------------------------------------------------------------------ #
    goal_col = total_cols - SAFE_END + 1
    goal     = GoalPost(goal_col * bs, bs)

    all_objects = [*floor_blocks, *platform_blocks, *fires, goal]

    return {
        "floor_blocks":    floor_blocks,
        "platform_blocks": platform_blocks,
        "fires":           fires,
        "goal":            goal,
        "level_width":     level_width,
        "all_objects":     all_objects,
    }


# ---------------------------------------------------------------------------
# Menu  (unchanged from previous refactor)
# ---------------------------------------------------------------------------

COL_CARD_IDLE  = (25,  32,  60)
COL_CARD_SEL   = (35,  50, 100)
COL_BORDER_SEL = (255, 210,  50)
COL_BORDER_IDL = (60,  70, 120)
COL_TITLE      = (255, 230,  80)
COL_WHITE      = (240, 240, 255)
COL_DIM        = (130, 140, 170)
COL_BTN_FACE   = (50,  160,  90)
COL_BTN_HOV    = (70,  210, 110)
COL_BTN_TEXT   = (10,   30,  15)

AVAILABLE_CHARACTERS = ["NinjaFrog", "PinkMan"]


class Particle:
    def __init__(self):
        self.reset(born=False)

    def reset(self, born=True):
        self.x     = random.randint(0, WIDTH)
        self.y     = random.randint(0, HEIGHT) if not born else HEIGHT + 5
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
    ANIM_DELAY    = 6
    PREVIEW_SCALE = 5

    def __init__(self, sprite_name: str, cx: int, cy: int):
        self.sprite_name = sprite_name
        self.cx, self.cy = cx, cy
        self.card_w, self.card_h = 220, 280

        sheets     = load_sprite_sheets("MainCharacters", sprite_name, 32, 32, True)
        raw_frames = sheets["idle_right"]
        self.frames = [
            pygame.transform.scale(
                f, (f.get_width() * self.PREVIEW_SCALE // 2,
                    f.get_height() * self.PREVIEW_SCALE // 2)
            ) for f in raw_frames
        ]
        self.anim_count = 0
        self._card_rect = pygame.Rect(cx - self.card_w // 2, cy - self.card_h // 2,
                                      self.card_w, self.card_h)

    @property
    def _current_frame(self):
        return self.frames[(self.anim_count // self.ANIM_DELAY) % len(self.frames)]

    def update(self):
        self.anim_count += 1

    def draw(self, surface, selected: bool):
        border_col = COL_BORDER_SEL if selected else COL_BORDER_IDL
        face_col   = COL_CARD_SEL   if selected else COL_CARD_IDLE

        shadow = pygame.Surface((self.card_w + 8, self.card_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 80), shadow.get_rect(), border_radius=16)
        surface.blit(shadow, (self._card_rect.x - 4, self._card_rect.y + 6))

        pygame.draw.rect(surface, face_col,   self._card_rect, border_radius=14)
        pygame.draw.rect(surface, border_col, self._card_rect, 4 if selected else 2, border_radius=14)

        f = self._current_frame
        surface.blit(f, (self.cx - f.get_width() // 2, self._card_rect.y + 30))

        lbl = font_small.render(self.sprite_name, True, COL_WHITE if selected else COL_DIM)
        surface.blit(lbl, (self.cx - lbl.get_width() // 2, self._card_rect.bottom - 52))

        if selected:
            hint = font_small.render("selected", True, COL_BORDER_SEL)
            surface.blit(hint, (self.cx - hint.get_width() // 2, self._card_rect.bottom - 24))

    def is_hovered(self, mx, my):
        return self._card_rect.collidepoint(mx, my)


class Menu:
    def __init__(self, window: pygame.Surface):
        self.window  = window
        self.clock   = pygame.time.Clock()
        self.selected_index = 0
        self.bg_image   = get_background("Blue.png")
        self.overlay    = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((5, 8, 20, 185))
        self.particles  = [Particle() for _ in range(60)]
        spacing = 240
        self.cards = [
            CharacterCard(AVAILABLE_CHARACTERS[0], WIDTH // 2 - spacing, HEIGHT // 2 - 10),
            CharacterCard(AVAILABLE_CHARACTERS[1], WIDTH // 2 + spacing, HEIGHT // 2 - 10),
        ]
        btn_w, btn_h = 280, 64
        self._btn_rect = pygame.Rect(WIDTH // 2 - btn_w // 2,
                                     HEIGHT // 2 + 190, btn_w, btn_h)
        self._title_t  = 0.0

    def run(self) -> str:
        self.running = True
        while self.running:
            self.clock.tick(FPS)
            result = self._handle_events()
            if result:
                return result
            self._update()
            self._draw()
        return AVAILABLE_CHARACTERS[self.selected_index]

    def _handle_events(self):
        mx, my = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); quit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT,  pygame.K_a):
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
        for p in self.particles: p.update()
        for c in self.cards:     c.update()
        self._title_t += 0.04

    def _draw(self):
        iw = self.bg_image.get_width()
        ih = self.bg_image.get_height()
        for col in range(WIDTH  // iw + 2):
            for row in range(HEIGHT // ih + 2):
                self.window.blit(self.bg_image, (col * iw, row * ih))
        self.window.blit(self.overlay, (0, 0))
        for p in self.particles: p.draw(self.window)

        pulse = 1.0 + 0.025 * math.sin(self._title_t)
        ts    = font_large.render("PLATFORMER", True, COL_TITLE)
        tw, th = int(ts.get_width() * pulse), int(ts.get_height() * pulse)
        ts    = pygame.transform.smoothscale(ts, (tw, th))
        self.window.blit(ts, (WIDTH // 2 - tw // 2, 60))

        draw_text_centered(self.window, "Choose your character",
                           COL_DIM, WIDTH // 2, 155, font_small)

        for i, card in enumerate(self.cards):
            card.draw(self.window, selected=(i == self.selected_index))

        draw_text_centered(self.window, "◀  ▶  arrow keys to navigate",
                           COL_DIM, WIDTH // 2, HEIGHT // 2 + 165, font_small)

        mx, my    = pygame.mouse.get_pos()
        btn_color = COL_BTN_HOV if self._btn_rect.collidepoint(mx, my) else COL_BTN_FACE
        sr = self._btn_rect.inflate(6, 6).move(3, 4)
        ss = pygame.Surface(sr.size, pygame.SRCALPHA)
        pygame.draw.rect(ss, (0, 0, 0, 70), ss.get_rect(), border_radius=14)
        self.window.blit(ss, sr.topleft)
        pygame.draw.rect(self.window, btn_color,  self._btn_rect, border_radius=12)
        pygame.draw.rect(self.window, COL_WHITE,   self._btn_rect, 2, border_radius=12)
        bl = font_small.render("▶  START GAME", True, COL_BTN_TEXT)
        self.window.blit(bl, (self._btn_rect.centerx - bl.get_width()  // 2,
                               self._btn_rect.centery - bl.get_height() // 2))
        pygame.display.update()


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

# Transition overlay colours
COL_TRANSITION_BG   = (10,  20,  10, 200)
COL_TRANSITION_TEXT = (80, 240, 100)
COL_DEAD_BG         = (30,   5,   5, 200)
COL_DEAD_TEXT       = (240,  60,  60)

# HUD colours
COL_HUD_BG     = (0,   0,   0, 110)
COL_HP_FULL    = (50, 200,  80)
COL_HP_MID     = (220, 200,  30)
COL_HP_LOW     = (220,  50,  30)
COL_PROGRESS   = (80,  160, 255)


class Game:
    BLOCK_SIZE        = 96
    SCROLL_AREA_WIDTH = 200

    # Transition durations in frames
    LEVEL_COMPLETE_FRAMES = 90   # 1.5 s "LEVEL COMPLETE" flash
    DEAD_FRAMES           = 120  # 2.0 s "GAME OVER" screen

    def __init__(self, window: pygame.Surface, sprite_name: str = "NinjaFrog"):
        self.window      = window
        self.clock       = pygame.time.Clock()
        self.sprite_name = sprite_name
        self.bg_image    = get_background("Blue.png")

        self.score   = 0
        self.level   = 1
        self.running = False

        # Transition state
        self._transition       = None   # "complete" | "dead" | None
        self._transition_timer = 0

        self._build_scene()

    # ------------------------------------------------------------------
    # Scene construction
    # ------------------------------------------------------------------

    def _build_scene(self):
        """Generate a fresh level and (re)create the player."""
        bs  = self.BLOCK_SIZE
        lvl = generate_level(self.level, bs)

        self.level_width     = lvl["level_width"]
        self.fires           = lvl["fires"]
        self.goal            = lvl["goal"]
        self.objects         = lvl["all_objects"]
        self.offset_x        = 0

        # Create a fresh player; health is managed externally on level-up
        self.player = Player(2 * bs, HEIGHT - bs * 2 - 50, 50, 50,
                             sprite_name=self.sprite_name)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self):
        self.running = True
        self._loop()

    def restart(self):
        self.score = 0
        self.level = 1
        self._build_scene()
        self.run()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _advance_level(self):
        """Move to the next level, preserving score and partially healing player."""
        old_health   = self.player.health
        self.level  += 1
        self.score  += 200 * self.level
        self._build_scene()
        # Reward: +25 HP on level up, capped at 100
        self.player.health = min(100, old_health + 25)
        self._transition       = None
        self._transition_timer = 0

    # ------------------------------------------------------------------
    # Private — per-frame logic
    # ------------------------------------------------------------------

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); quit()
            if event.type == pygame.KEYDOWN:
                if self._transition == "dead":
                    # Any key restarts from level 1 on death screen
                    if event.key not in (pygame.K_ESCAPE,):
                        self.score = 0
                        self.level = 1
                        self._build_scene()
                        self._transition = None
                        return
                if event.key == pygame.K_SPACE and self.player.jump_count < 2:
                    if self._transition is None:
                        self.player.jump()
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def _update(self):
        # While a non-dead transition is active just tick the clock
        if self._transition == "complete":
            self._transition_timer += 1
            if self._transition_timer >= self.LEVEL_COMPLETE_FRAMES:
                self._advance_level()
            return

        if self._transition == "dead":
            self._transition_timer += 1
            return

        # --- Normal update ---
        self.player.loop(FPS)
        for fire in self.fires:
            fire.loop()
        handle_move(self.player, self.objects)

        # Death check
        if self.player.health <= 0:
            self._transition       = "dead"
            self._transition_timer = 0
            return

        # Level-complete check: player touches the goal post
        if pygame.sprite.collide_mask(self.player, self.goal):
            self._transition       = "complete"
            self._transition_timer = 0
            return

        # Horizontal scrolling (clamped to level bounds)
        p = self.player
        if ((p.rect.right - self.offset_x >= WIDTH - self.SCROLL_AREA_WIDTH) and p.x_vel > 0) or \
           ((p.rect.left  - self.offset_x <= self.SCROLL_AREA_WIDTH)          and p.x_vel < 0):
            self.offset_x = max(0, min(self.offset_x + p.x_vel,
                                       self.level_width - WIDTH))

    def _draw_background(self):
        """Tile the background image across the current viewport."""
        iw = self.bg_image.get_width()
        ih = self.bg_image.get_height()
        first_col = self.offset_x // iw
        for col in range(first_col, first_col + WIDTH // iw + 2):
            for row in range(HEIGHT // ih + 2):
                self.window.blit(self.bg_image, (col * iw - self.offset_x, row * ih))

    def _draw_hud(self):
        bs = self.BLOCK_SIZE

        # --- semi-transparent HUD panel ---
        hud = pygame.Surface((340, 100), pygame.SRCALPHA)
        hud.fill(COL_HUD_BG)
        pygame.draw.rect(hud, (255, 255, 255, 40), hud.get_rect(), 1, border_radius=8)
        self.window.blit(hud, (10, 10))

        # HP bar
        bar_x, bar_y, bar_w, bar_h = 20, 20, 200, 18
        pygame.draw.rect(self.window, (60, 20, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        hp_ratio = max(0, self.player.health / 100)
        hp_col   = COL_HP_FULL if hp_ratio > 0.5 else (COL_HP_MID if hp_ratio > 0.25 else COL_HP_LOW)
        pygame.draw.rect(self.window, hp_col,
                         (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=4)
        pygame.draw.rect(self.window, (200, 200, 200),
                         (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        draw_text(self.window, f"HP  {self.player.health}", (220, 220, 220),
                  bar_x + bar_w + 10, bar_y - 2, font_small)

        # Score & level
        draw_text(self.window, f"Score  {self.score}", (220, 220, 220), 20, 48, font_small)
        draw_text(self.window, f"Level  {self.level}", (220, 220, 220), 180, 48, font_small)

        # ESC hint
        hint = font_small.render("ESC — menu", True, (100, 100, 100))
        self.window.blit(hint, (WIDTH - hint.get_width() - 14, 14))

        # --- Level progress bar at bottom ---
        prog_ratio = min(1.0, self.player.rect.x / max(1, self.level_width - WIDTH))
        pb_x, pb_y, pb_w, pb_h = 10, HEIGHT - 18, WIDTH - 20, 8
        pygame.draw.rect(self.window, (30, 30, 50),  (pb_x, pb_y, pb_w, pb_h), border_radius=4)
        pygame.draw.rect(self.window, COL_PROGRESS,
                         (pb_x, pb_y, int(pb_w * prog_ratio), pb_h), border_radius=4)
        pygame.draw.rect(self.window, (80, 80, 120),
                         (pb_x, pb_y, pb_w, pb_h), 1, border_radius=4)
        # Flag icon at far right of bar
        flag_x = pb_x + pb_w - 6
        pygame.draw.line(self.window, (255, 215, 0), (flag_x, pb_y - 6), (flag_x, pb_y + pb_h + 4), 2)
        pts = [(flag_x, pb_y - 6), (flag_x + 10, pb_y - 2), (flag_x, pb_y + 2)]
        pygame.draw.polygon(self.window, (50, 210, 80), pts)

    def _draw_transition(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        if self._transition == "complete":
            overlay.fill(COL_TRANSITION_BG)
            self.window.blit(overlay, (0, 0))
            t = self._transition_timer / self.LEVEL_COMPLETE_FRAMES
            alpha = int(255 * min(1.0, t * 4))             # fade in quickly
            # Main text
            msg   = font_large.render("LEVEL COMPLETE!", True, COL_TRANSITION_TEXT)
            msg.set_alpha(alpha)
            self.window.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 60))
            # Bonus points
            bonus = font_small.render(f"+{200 * (self.level + 1)} points", True, (200, 255, 160))
            bonus.set_alpha(alpha)
            self.window.blit(bonus, (WIDTH // 2 - bonus.get_width() // 2, HEIGHT // 2 + 20))
            # Next level hint
            sub = font_small.render(f"Preparing level {self.level + 1}...", True, (150, 220, 150))
            sub.set_alpha(alpha)
            self.window.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 60))

        elif self._transition == "dead":
            overlay.fill(COL_DEAD_BG)
            self.window.blit(overlay, (0, 0))
            t     = min(1.0, self._transition_timer / 30)
            alpha = int(255 * t)
            msg   = font_large.render("GAME OVER", True, COL_DEAD_TEXT)
            msg.set_alpha(alpha)
            self.window.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 80))
            sc    = font_medium.render(f"Score: {self.score}", True, (240, 200, 200))
            sc.set_alpha(alpha)
            self.window.blit(sc, (WIDTH // 2 - sc.get_width() // 2, HEIGHT // 2))
            if self._transition_timer > 60:
                hint = font_small.render("Press any key to try again  •  ESC for menu",
                                         True, (180, 120, 120))
                hint.set_alpha(alpha)
                self.window.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 70))

    def _draw(self):
        self._draw_background()
        for obj in self.objects:
            obj.draw(self.window, self.offset_x)
        self.player.draw(self.window, self.offset_x)
        self._draw_hud()
        if self._transition:
            self._draw_transition()
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
        chosen = menu.run()
        game   = Game(window, chosen)
        game.run()
