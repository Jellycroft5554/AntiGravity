"""
Endless Runner - Chunk 1, 2, 3: Core Engine, Modes, Obstacles, and Gameplay Loop
A complete 2D endless-runner game built in Python using Pygame.
Requires only: pip install pygame
"""

import sys
import math
import random
import pygame

# ============================================================================
# GLOBAL CONFIGURATION & CONSTANTS
# ============================================================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Physics Constants (Delta-time based)
GRAVITY = 1850.0            # Downward acceleration (px/s^2)
JUMP_STRENGTH = -740.0       # Upward launch velocity (px/s) -> apex ~148px
PLAYER_SPEED = 380.0        # Base horizontal scrolling speed of the world (px/s)
GROUND_Y = 560              # Y coordinate of the ground surface

# Color Palette
COLOR_BLACK = (20, 24, 30)
COLOR_WHITE = (248, 250, 252)
COLOR_DARK_SLATE = (15, 23, 42)
COLOR_PANEL_BG = (30, 41, 59)
COLOR_PANEL_BORDER = (51, 65, 85)
COLOR_PANEL_HIGHLIGHT = (56, 189, 248)
COLOR_ACCENT_GOLD = (251, 191, 36)
COLOR_ACCENT_CYAN = (6, 182, 212)
COLOR_ACCENT_RED = (239, 68, 68)
COLOR_TEXT_PRIMARY = (241, 245, 249)
COLOR_TEXT_MUTED = (148, 163, 184)


# ============================================================================
# GAME ENUMS & DATA DEFINITIONS
# ============================================================================
class GameState:
    MAIN_MENU = "MAIN_MENU"
    CHAR_SELECT = "CHAR_SELECT"
    MODE_SELECT = "MODE_SELECT"
    PLAYING = "PLAYING"
    GAME_OVER = "GAME_OVER"


class CharacterType:
    CLASSIC = "CLASSIC"
    DINOSAUR = "DINOSAUR"
    SANDDUNE = "SANDDUNE"
    CAR = "CAR"

    ALL = [CLASSIC, DINOSAUR, SANDDUNE, CAR]

    INFO = {
        CLASSIC: {
            "title": "Classic Stickman",
            "desc": "Agile, nimble, and timeless.",
            "width": 32,
            "height": 72,
        },
        DINOSAUR: {
            "title": "Cartoon T-Rex",
            "desc": "Mighty prehistoric dasher.",
            "width": 82,
            "height": 80,
        },
        SANDDUNE: {
            "title": "Rolling Sand Dune",
            "desc": "A perpetual desert vortex.",
            "width": 56,
            "height": 56,
        },
        CAR: {
            "title": "Turbo Red Coupe",
            "desc": "Aerodynamic hot-rod.",
            "width": 92,
            "height": 46,
        },
    }


class GameMode:
    DAY = "DAY"
    DESERT = "DESERT"
    NIGHT = "NIGHT"
    MARS = "MARS"

    ALL = [DAY, DESERT, NIGHT, MARS]

    INFO = {
        DAY: {
            "desc": "Classic grassy plains daytime environment.",
            "color": (56, 189, 248),
        },
        DESERT: {
            "desc": "Scorching sands with a dynamic day/night cycle.",
            "color": (245, 158, 11),
        },
        NIGHT: {
            "desc": "A quiet, starlit grassy plains environment.",
            "color": (168, 85, 247),
        },
        MARS: {
            "desc": "The rusty red planet with craters and scrap.",
            "color": (239, 68, 68),
        },
    }


def lerp_color(c1, c2, t):
    """Linearly interpolates between two RGB colors by factor t (0.0 to 1.0)."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


# ============================================================================
# PARTICLE SYSTEM
# ============================================================================
class Particle:
    def __init__(self, x, y, vx, vy, color, size, life):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.max_life = life
        self.life = life

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha_ratio = max(0.0, min(1.0, self.life / self.max_life))
        current_size = max(1.0, self.size * alpha_ratio)
        r, g, b = self.color[:3]
        particle_surf = pygame.Surface((int(current_size * 2) + 2, int(current_size * 2) + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            particle_surf,
            (r, g, b, int(200 * alpha_ratio)),
            (int(current_size) + 1, int(current_size) + 1),
            int(current_size)
        )
        surface.blit(particle_surf, (self.x - current_size, self.y - current_size))


class ParticleEmitter:
    def __init__(self):
        self.particles = []

    def emit_dust(self, x, y, count=3, color=(200, 185, 155), speed_scale=1.0):
        for _ in range(count):
            vx = random.uniform(-140, -40) * speed_scale
            vy = random.uniform(-40, -5)
            size = random.uniform(2.5, 5.0)
            life = random.uniform(0.2, 0.45)
            self.particles.append(Particle(x, y, vx, vy, color, size, life))

    def emit_jump_burst(self, x, y, count=8, color=(220, 215, 195)):
        for _ in range(count):
            angle = random.uniform(math.pi * 0.7, math.pi * 1.3)
            spd = random.uniform(60, 180)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd * 0.4
            size = random.uniform(3.0, 6.0)
            life = random.uniform(0.25, 0.5)
            self.particles.append(Particle(x, y, vx, vy, color, size, life))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def clear(self):
        self.particles.clear()


# ============================================================================
# PLAYER CLASS & CHARACTER RENDERERS
# ============================================================================
class Player:
    def __init__(self, x=190, char_type=CharacterType.CLASSIC):
        self.base_x = x
        self.x = float(x)
        self.y = float(GROUND_Y)
        self.vy = 0.0
        self.is_on_ground = True
        self.char_type = char_type

        self.anim_timer = 0.0
        self.dust_timer = 0.0
        self.car_tilt_angle = 0.0
        self.car_visual_offset_x = 0.0
        self.roll_angle = 0.0
        self.emitter = ParticleEmitter()
        self.sync_dimensions()

    def sync_dimensions(self):
        info = CharacterType.INFO[self.char_type]
        self.width = info["width"]
        self.height = info["height"]
        if self.is_on_ground:
            self.y = float(GROUND_Y)

    def set_character(self, char_type):
        if char_type in CharacterType.ALL:
            self.char_type = char_type
            self.sync_dimensions()

    def reset(self):
        self.x = float(self.base_x)
        self.y = float(GROUND_Y)
        self.vy = 0.0
        self.is_on_ground = True
        self.anim_timer = 0.0
        self.dust_timer = 0.0
        self.car_tilt_angle = 0.0
        self.car_visual_offset_x = 0.0
        self.roll_angle = 0.0
        self.emitter.clear()
        self.sync_dimensions()

    def jump(self):
        if self.is_on_ground:
            self.vy = JUMP_STRENGTH
            self.is_on_ground = False
            foot_x = self.x + self.width * 0.5
            self.emitter.emit_jump_burst(foot_x, GROUND_Y, count=10)

    def update(self, dt, speed_mult=1.0):
        # Physics Update
        if not self.is_on_ground:
            self.vy += GRAVITY * dt
            self.y += self.vy * dt
            if self.y >= GROUND_Y:
                self.y = float(GROUND_Y)
                self.vy = 0.0
                self.is_on_ground = True
                foot_x = self.x + self.width * 0.5
                self.emitter.emit_jump_burst(foot_x, GROUND_Y, count=6)
        else:
            self.y = float(GROUND_Y)
            self.vy = 0.0

        # Animation state updates
        self.anim_timer += dt * speed_mult

        radius = self.width * 0.5
        roll_speed = (PLAYER_SPEED * speed_mult) / max(1.0, radius)
        self.roll_angle = (self.roll_angle + roll_speed * dt) % (2 * math.pi)

        if self.is_on_ground and speed_mult > 0.0:
            self.dust_timer += dt
            if self.dust_timer >= 0.09:
                self.dust_timer = 0.0
                dust_color = (210, 180, 140) if self.char_type == CharacterType.SANDDUNE else (180, 175, 160)
                self.emitter.emit_dust(self.x + 8, GROUND_Y - 2, count=2, color=dust_color, speed_scale=speed_mult)

        if self.char_type == CharacterType.CAR:
            if not self.is_on_ground:
                if self.vy < 0:
                    target_tilt = -14.0
                    target_offset = 36.0 * (abs(self.vy) / abs(JUMP_STRENGTH))
                else:
                    target_tilt = 12.0
                    target_offset = 18.0 * max(0.0, 1.0 - (self.y - (GROUND_Y - 140)) / 140.0)
                self.car_tilt_angle += (target_tilt - self.car_tilt_angle) * min(1.0, dt * 14.0)
                self.car_visual_offset_x += (target_offset - self.car_visual_offset_x) * min(1.0, dt * 12.0)
            else:
                self.car_tilt_angle += (0.0 - self.car_tilt_angle) * min(1.0, dt * 20.0)
                self.car_visual_offset_x += (0.0 - self.car_visual_offset_x) * min(1.0, dt * 20.0)
        else:
            self.car_tilt_angle = 0.0
            self.car_visual_offset_x = 0.0

        self.emitter.update(dt)

    def get_hitbox(self):
        curr_x = self.x + (self.car_visual_offset_x if self.char_type == CharacterType.CAR else 0.0)
        top_y = self.y - self.height

        if self.char_type == CharacterType.CLASSIC:
            hb_w, hb_h = 22, 66
            hb_x = curr_x + (self.width - hb_w) * 0.5
            return pygame.Rect(int(hb_x), int(self.y - hb_h), hb_w, hb_h)

        elif self.char_type == CharacterType.DINOSAUR:
            hb_w, hb_h = 64, 72
            hb_x = curr_x + 10
            return pygame.Rect(int(hb_x), int(self.y - hb_h), hb_w, hb_h)

        elif self.char_type == CharacterType.SANDDUNE:
            inset = 5
            hb_w, hb_h = self.width - inset * 2, self.height - inset * 2
            hb_x, hb_y = curr_x + inset, self.y - self.height + inset
            return pygame.Rect(int(hb_x), int(hb_y), hb_w, hb_h)

        elif self.char_type == CharacterType.CAR:
            hb_w, hb_h = 84, 36
            hb_x = curr_x + 4
            return pygame.Rect(int(hb_x), int(self.y - hb_h), hb_w, hb_h)

        return pygame.Rect(int(curr_x), int(top_y), int(self.width), int(self.height))

    def draw(self, surface, debug_hitbox=False):
        self.emitter.draw(surface)
        curr_x = self.x + (self.car_visual_offset_x if self.char_type == CharacterType.CAR else 0.0)
        curr_y = self.y

        if self.char_type == CharacterType.CLASSIC:
            self._draw_classic(surface, curr_x, curr_y)
        elif self.char_type == CharacterType.DINOSAUR:
            self._draw_dinosaur(surface, curr_x, curr_y)
        elif self.char_type == CharacterType.SANDDUNE:
            self._draw_sanddune(surface, curr_x, curr_y)
        elif self.char_type == CharacterType.CAR:
            self._draw_car(surface, curr_x, curr_y)

        if debug_hitbox:
            pygame.draw.rect(surface, (255, 0, 0), self.get_hitbox(), 2)

    def draw_preview(self, surface, center_x, center_y, scale=1.4):
        baseline_y = center_y + (self.height * 0.5 * scale)
        start_x = center_x - (self.width * 0.5 * scale)
        temp_w, temp_h = int(self.width * 1.6 + 60), int(self.height * 1.6 + 60)
        temp_surf = pygame.Surface((temp_w, temp_h), pygame.SRCALPHA)
        local_x, local_y = 30, temp_h - 20

        if self.char_type == CharacterType.CLASSIC:
            self._draw_classic(temp_surf, local_x, local_y)
        elif self.char_type == CharacterType.DINOSAUR:
            self._draw_dinosaur(temp_surf, local_x, local_y)
        elif self.char_type == CharacterType.SANDDUNE:
            self._draw_sanddune(temp_surf, local_x, local_y)
        elif self.char_type == CharacterType.CAR:
            self._draw_car(temp_surf, local_x, local_y, is_preview=True)

        scaled_w, scaled_h = int(temp_w * scale), int(temp_h * scale)
        scaled_surf = pygame.transform.smoothscale(temp_surf, (scaled_w, scaled_h))
        surface.blit(scaled_surf, (center_x - scaled_w * 0.5, center_y - scaled_h * 0.5))

    def _draw_classic(self, surface, x, y):
        color = (18, 18, 20)
        thick = 4
        head_radius = 8
        head_x, head_y = x + 16, y - 62
        pygame.draw.circle(surface, color, (int(head_x), int(head_y)), head_radius)
        neck_y, pelvis_y = head_y + head_radius, y - 28
        torso_x = head_x
        pygame.draw.line(surface, color, (int(torso_x), int(neck_y)), (int(torso_x), int(pelvis_y)), thick)

        if self.is_on_ground:
            cycle = self.anim_timer * 15.0
            leg1_angle = math.sin(cycle) * 0.7
            leg2_angle = math.sin(cycle + math.pi) * 0.7
            arm1_angle = math.sin(cycle + math.pi) * 0.6
            arm2_angle = math.sin(cycle) * 0.6
        else:
            leg1_angle, leg2_angle = 0.5, -0.6
            arm1_angle, arm2_angle = -0.9, -0.7

        leg_len = 15
        for angle in (leg1_angle, leg2_angle):
            knee_x = torso_x + math.sin(angle) * leg_len
            knee_y = pelvis_y + math.cos(angle) * leg_len
            foot_x = knee_x + math.sin(angle * 0.7 + 0.3) * leg_len
            foot_y = knee_y + math.cos(angle * 0.7 + 0.3) * leg_len
            pygame.draw.line(surface, color, (int(torso_x), int(pelvis_y)), (int(knee_x), int(knee_y)), thick)
            pygame.draw.line(surface, color, (int(knee_x), int(knee_y)), (int(foot_x), int(foot_y)), thick)

        shoulder_y = neck_y + 6
        arm_len = 12
        for angle in (arm1_angle, arm2_angle):
            elbow_x = torso_x + math.sin(angle) * arm_len
            elbow_y = shoulder_y + math.cos(angle) * arm_len
            hand_x = elbow_x + math.sin(angle + 0.4) * (arm_len * 0.8)
            hand_y = elbow_y + math.cos(angle + 0.4) * (arm_len * 0.8)
            pygame.draw.line(surface, color, (int(torso_x), int(shoulder_y)), (int(elbow_x), int(elbow_y)), thick - 1)
            pygame.draw.line(surface, color, (int(elbow_x), int(elbow_y)), (int(hand_x), int(hand_y)), thick - 1)

    def _draw_dinosaur(self, surface, x, y):
        dino_green = (46, 125, 50)
        belly_green = (129, 199, 132)
        eye_color = (255, 255, 255)
        pupil_color = (20, 20, 20)
        teeth_color = (250, 250, 240)

        if self.is_on_ground:
            leg_cycle = self.anim_timer * 13.0
            bob = abs(math.sin(leg_cycle)) * 4.0
            leg1_phase = math.sin(leg_cycle) * 0.65
            leg2_phase = math.sin(leg_cycle + math.pi) * 0.65
            tail_sway = math.sin(leg_cycle) * 3.0
        else:
            bob = 0.0
            leg1_phase, leg2_phase = 0.5, -0.5
            tail_sway = 2.0

        base_y = y - bob

        # Back leg
        hip2_x, hip2_y = x + 38, base_y - 28
        k2_x, k2_y = hip2_x + math.sin(leg2_phase) * 16, hip2_y + math.cos(leg2_phase) * 16
        f2_x = k2_x + math.sin(leg2_phase + 0.2) * 14
        f2_y = min(y, k2_y + math.cos(leg2_phase + 0.2) * 14)
        pygame.draw.line(surface, (36, 100, 40), (int(hip2_x), int(hip2_y)), (int(k2_x), int(k2_y)), 7)
        pygame.draw.line(surface, (36, 100, 40), (int(k2_x), int(k2_y)), (int(f2_x), int(f2_y)), 5)
        pygame.draw.line(surface, (36, 100, 40), (int(f2_x - 4), int(f2_y)), (int(f2_x + 6), int(f2_y)), 4)

        # Tail
        tail_poly = [
            (x + 22, base_y - 36),
            (x - 14, base_y - 48 + tail_sway),
            (x - 10, base_y - 38 + tail_sway),
            (x + 25, base_y - 24),
        ]
        pygame.draw.polygon(surface, dino_green, tail_poly)

        # Body
        body_rect = pygame.Rect(int(x + 18), int(base_y - 54), 38, 32)
        pygame.draw.ellipse(surface, dino_green, body_rect)
        belly_rect = pygame.Rect(int(x + 24), int(base_y - 44), 28, 20)
        pygame.draw.ellipse(surface, belly_green, belly_rect)

        # Head
        head_poly = [
            (x + 36, base_y - 50), (x + 42, base_y - 74), (x + 78, base_y - 74), (x + 82, base_y - 56),
            (x + 58, base_y - 56), (x + 76, base_y - 50), (x + 72, base_y - 42), (x + 44, base_y - 42),
        ]
        pygame.draw.polygon(surface, dino_green, head_poly)

        teeth = [
            [(x + 60, base_y - 56), (x + 63, base_y - 52), (x + 66, base_y - 56)],
            [(x + 67, base_y - 56), (x + 70, base_y - 52), (x + 73, base_y - 56)],
            [(x + 74, base_y - 56), (x + 77, base_y - 52), (x + 80, base_y - 56)],
        ]
        for t in teeth:
            pygame.draw.polygon(surface, teeth_color, t)

        pygame.draw.circle(surface, eye_color, (int(x + 56), int(base_y - 66)), 5)
        pygame.draw.circle(surface, pupil_color, (int(x + 58), int(base_y - 66)), 2)

        # Arm
        arm_poly = [(x + 46, base_y - 38), (x + 54, base_y - 35), (x + 52, base_y - 32)]
        pygame.draw.polygon(surface, dino_green, arm_poly)
        pygame.draw.line(surface, (25, 70, 30), (x + 54, base_y - 35), (x + 56, base_y - 36), 2)

        # Front Leg
        hip1_x, hip1_y = x + 34, base_y - 28
        k1_x, k1_y = hip1_x + math.sin(leg1_phase) * 16, hip1_y + math.cos(leg1_phase) * 16
        f1_x = k1_x + math.sin(leg1_phase + 0.2) * 14
        f1_y = min(y, k1_y + math.cos(leg1_phase + 0.2) * 14)
        pygame.draw.line(surface, dino_green, (int(hip1_x), int(hip1_y)), (int(k1_x), int(k1_y)), 8)
        pygame.draw.line(surface, dino_green, (int(k1_x), int(k1_y)), (int(f1_x), int(f1_y)), 6)
        pygame.draw.line(surface, (25, 70, 30), (int(f1_x - 4), int(f1_y)), (int(f1_x + 7), int(f1_y)), 5)

    def _draw_sanddune(self, surface, x, y):
        radius = int(self.width * 0.5)
        cx, cy = x + radius, y - radius
        sand_main = (222, 168, 106)
        sand_dark = (194, 137, 76)
        sand_light = (245, 206, 154)

        pygame.draw.circle(surface, sand_main, (int(cx), int(cy)), radius)

        for i in range(4):
            angle = self.roll_angle + (i * (math.pi / 2))
            arc_offset_x = math.cos(angle) * (radius * 0.55)
            arc_offset_y = math.sin(angle) * (radius * 0.55)
            ridge_x, ridge_y = cx + arc_offset_x, cy + arc_offset_y
            ridge_r = max(2, int(radius * 0.35 * abs(math.sin(angle + 0.3))))
            color = sand_light if math.sin(angle) > 0 else sand_dark
            pygame.draw.circle(surface, color, (int(ridge_x), int(ridge_y)), ridge_r)

        spiral_pts = []
        for step in range(8):
            step_angle = self.roll_angle + (step * 0.4)
            dist = (step / 8.0) * (radius * 0.8)
            px, py = cx + math.cos(step_angle) * dist, cy + math.sin(step_angle) * dist
            spiral_pts.append((int(px), int(py)))
        if len(spiral_pts) > 1:
            pygame.draw.lines(surface, sand_dark, False, spiral_pts, 3)

        pygame.draw.circle(surface, sand_dark, (int(cx), int(cy)), radius, 2)
        highlight_rect = pygame.Rect(int(cx - radius + 3), int(cy - radius + 3), radius * 2 - 6, radius * 2 - 6)
        pygame.draw.arc(surface, sand_light, highlight_rect, math.pi * 0.25, math.pi * 0.85, 3)

    def _draw_car(self, surface, x, y, is_preview=False):
        car_red = (220, 38, 38)
        car_roof = (185, 28, 28)
        car_dark = (153, 27, 27)
        glass_blue = (186, 230, 253)
        light_yellow = (254, 240, 138)
        wheel_black = (30, 30, 30)
        rim_silver = (203, 213, 225)

        tilt = 0.0 if is_preview else self.car_tilt_angle
        w, h = int(self.width), int(self.height)
        car_surf = pygame.Surface((w + 10, h + 10), pygame.SRCALPHA)
        bx, by = 4, h - 22

        body_poly = [
            (bx + 4, by + 12), (bx + 88, by + 12), (bx + 86, by + 4), (bx + 74, by),
            (bx + 62, by - 14), (bx + 28, by - 14), (bx + 16, by), (bx + 4, by + 4),
        ]
        pygame.draw.polygon(car_surf, car_red, body_poly)
        pygame.draw.polygon(car_surf, car_dark, body_poly, 2)
        pygame.draw.line(car_surf, car_roof, (bx + 28, by - 14), (bx + 62, by - 14), 3)

        front_window = [(bx + 46, by - 12), (bx + 59, by - 12), (bx + 68, by), (bx + 46, by)]
        pygame.draw.polygon(car_surf, glass_blue, front_window)
        rear_window = [(bx + 24, by), (bx + 32, by - 12), (bx + 42, by - 12), (bx + 42, by)]
        pygame.draw.polygon(car_surf, glass_blue, rear_window)
        pygame.draw.line(car_surf, (255, 255, 255), (bx + 48, by - 10), (bx + 54, by - 2), 2)

        pygame.draw.polygon(car_surf, light_yellow, [(bx + 85, by + 3), (bx + 88, by + 5), (bx + 86, by + 9), (bx + 83, by + 8)])
        pygame.draw.rect(car_surf, (255, 100, 100), (bx + 4, by + 4, 3, 6))

        wheel_radius = 8
        wheel_y = by + 14
        wheel_xs = [bx + 22, bx + 70]
        wheel_angle = self.anim_timer * 18.0 if (self.is_on_ground or is_preview) else self.anim_timer * 8.0

        for wx in wheel_xs:
            pygame.draw.circle(car_surf, wheel_black, (int(wx), int(wheel_y)), wheel_radius)
            pygame.draw.circle(car_surf, rim_silver, (int(wx), int(wheel_y)), int(wheel_radius * 0.55))
            for spoke in range(4):
                sp_angle = wheel_angle + (spoke * (math.pi / 2))
                sx = wx + math.cos(sp_angle) * (wheel_radius * 0.5)
                sy = wheel_y + math.sin(sp_angle) * (wheel_radius * 0.5)
                pygame.draw.line(car_surf, (80, 80, 80), (int(wx), int(wheel_y)), (int(sx), int(sy)), 2)

        if abs(tilt) > 0.5:
            rotated_surf = pygame.transform.rotate(car_surf, -tilt)
            rot_rect = rotated_surf.get_rect()
            rot_rect.center = (int(x + w * 0.5), int(y - h * 0.5))
            surface.blit(rotated_surf, rot_rect.topleft)
        else:
            surface.blit(car_surf, (int(x), int(y - h - 4)))


# ============================================================================
# BACKGROUND SYSTEM
# ============================================================================
class BackgroundSystem:
    def __init__(self):
        self.mode = GameMode.DAY
        self.cloud_scroll = 0.0
        self.hill_scroll = 0.0
        self.plains_scroll = 0.0
        self.ground_scroll = 0.0
        
        self.desert_time = 0.0  # 0.0 to 1.0 cycle
        self.stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, int(GROUND_Y - 100))) for _ in range(100)]

        self.clouds = []
        for i in range(7):
            cx = (i * 220) + random.uniform(-40, 40)
            cy = random.uniform(50, 200)
            scale = random.uniform(0.7, 1.4)
            speed_mult = random.uniform(0.3, 0.7)
            self.clouds.append({"x": cx, "y": cy, "scale": scale, "spd": speed_mult})

    def update(self, dt, world_speed, mode):
        self.mode = mode
        self.cloud_scroll += world_speed * 0.15 * dt
        self.hill_scroll += world_speed * 0.30 * dt
        self.plains_scroll += world_speed * 0.60 * dt
        self.ground_scroll = (self.ground_scroll + world_speed * dt) % 60.0
        
        if self.mode == GameMode.DESERT:
            self.desert_time += dt * 0.05
            if self.desert_time > 1.0:
                self.desert_time -= 1.0

    def draw(self, surface):
        if self.mode == GameMode.DAY:
            self._draw_day(surface)
        elif self.mode == GameMode.NIGHT:
            self._draw_night(surface)
        elif self.mode == GameMode.DESERT:
            self._draw_desert(surface)
        elif self.mode == GameMode.MARS:
            self._draw_mars(surface)

    def _draw_sky_gradient(self, surface, top_color, bot_color):
        steps = 32
        strip_h = int(GROUND_Y / steps) + 1
        for i in range(steps):
            ratio = i / float(steps)
            c = lerp_color(top_color, bot_color, ratio)
            pygame.draw.rect(surface, c, (0, i * strip_h, SCREEN_WIDTH, strip_h))

    def _draw_sun(self, surface, x, y, core_color, glow_color):
        glow_surf = pygame.Surface((180, 180), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*glow_color, 45), (90, 90), 80)
        pygame.draw.circle(glow_surf, (*glow_color, 80), (90, 90), 55)
        surface.blit(glow_surf, (int(x) - 90, int(y) - 90))
        pygame.draw.circle(surface, core_color, (int(x), int(y)), 36)

    def _draw_moon(self, surface, x, y):
        pygame.draw.circle(surface, (240, 240, 255), (int(x), int(y)), 30)
        pygame.draw.circle(surface, (200, 200, 220), (int(x - 10), int(y - 5)), 6)
        pygame.draw.circle(surface, (200, 200, 220), (int(x + 5), int(y + 10)), 4)

    def _draw_stars(self, surface):
        for sx, sy in self.stars:
            intensity = random.randint(150, 255)
            surface.set_at((sx, sy), (intensity, intensity, intensity))

    def _draw_clouds(self, surface, color, shadow_color):
        for c in self.clouds:
            draw_x = (c["x"] - (self.cloud_scroll * c["spd"])) % (SCREEN_WIDTH + 300) - 150
            draw_y = c["y"]
            scale = c["scale"]
            puffs = [
                (draw_x, draw_y, int(20 * scale)),
                (draw_x + int(24 * scale), draw_y - int(10 * scale), int(26 * scale)),
                (draw_x + int(52 * scale), draw_y - int(4 * scale), int(22 * scale)),
                (draw_x + int(76 * scale), draw_y + int(4 * scale), int(16 * scale)),
            ]
            for px, py, pr in puffs:
                pygame.draw.circle(surface, shadow_color, (int(px), int(py + 4 * scale)), pr)
            for px, py, pr in puffs:
                pygame.draw.circle(surface, color, (int(px), int(py)), pr)

    def _draw_hills(self, surface, color, amp1, freq1, amp2, freq2, base_y):
        points = [(0, GROUND_Y)]
        segment_w = 160
        num_segs = int(SCREEN_WIDTH / segment_w) + 3
        offset = (self.hill_scroll) % segment_w
        for i in range(-1, num_segs):
            px = (i * segment_w) - offset
            py = base_y - math.sin((i + 1) * freq1) * amp1 - math.cos(i * freq2) * amp2
            points.append((px, py))
        points.append((SCREEN_WIDTH, GROUND_Y))
        pygame.draw.polygon(surface, color, points)

    def _draw_ground_texture(self, surface, base_color, mid_color, top_color, highlight_color):
        ground_h = SCREEN_HEIGHT - GROUND_Y
        pygame.draw.rect(surface, base_color, (0, GROUND_Y, SCREEN_WIDTH, ground_h))
        pygame.draw.rect(surface, mid_color, (0, GROUND_Y + 36, SCREEN_WIDTH, ground_h - 36))
        pygame.draw.rect(surface, top_color, (0, GROUND_Y, SCREEN_WIDTH, 14))
        pygame.draw.rect(surface, highlight_color, (0, GROUND_Y, SCREEN_WIDTH, 4))
        
        spacing = 40
        num_markers = int(SCREEN_WIDTH / spacing) + 3
        for i in range(-1, num_markers):
            gx = (i * spacing) - self.ground_scroll
            pygame.draw.line(surface, highlight_color, (gx, GROUND_Y), (gx + 4, GROUND_Y - 5), 2)
            pygame.draw.line(surface, highlight_color, (gx + 6, GROUND_Y), (gx + 9, GROUND_Y - 7), 2)
            if i % 2 == 0:
                pygame.draw.circle(surface, mid_color, (int(gx + 15), GROUND_Y + 22), 3)

    def _draw_day(self, surface):
        self._draw_sky_gradient(surface, (45, 125, 225), (145, 205, 255))
        self._draw_sun(surface, 1060, 120, (255, 245, 170), (255, 235, 130))
        self._draw_clouds(surface, (255, 255, 255), (220, 235, 245))
        self._draw_hills(surface, (110, 165, 130), 45, 1.1, 25, 0.7, GROUND_Y - 140)
        self._draw_hills(surface, (85, 145, 105), 22, 1.6, 0, 0, GROUND_Y - 65)
        self._draw_ground_texture(surface, (109, 76, 65), (78, 52, 46), (46, 125, 50), (76, 175, 80))

    def _draw_night(self, surface):
        self._draw_sky_gradient(surface, (10, 15, 30), (20, 30, 60))
        self._draw_stars(surface)
        self._draw_moon(surface, 1060, 120)
        self._draw_clouds(surface, (40, 50, 70), (25, 30, 45))
        self._draw_hills(surface, (20, 40, 40), 45, 1.1, 25, 0.7, GROUND_Y - 140)
        self._draw_hills(surface, (15, 30, 30), 22, 1.6, 0, 0, GROUND_Y - 65)
        self._draw_ground_texture(surface, (30, 20, 20), (15, 10, 10), (20, 50, 30), (30, 70, 40))

    def _draw_desert(self, surface):
        t = self.desert_time
        if t < 0.25: 
            factor = t / 0.25
            top = lerp_color((20, 30, 60), (255, 150, 80), factor)
            bot = lerp_color((10, 15, 30), (255, 200, 100), factor)
            light_val = lerp_color((50, 40, 40), (220, 180, 120), factor)
        elif t < 0.5: 
            factor = (t - 0.25) / 0.25
            top = lerp_color((255, 150, 80), (60, 160, 240), factor)
            bot = lerp_color((255, 200, 100), (180, 220, 255), factor)
            light_val = lerp_color((220, 180, 120), (255, 220, 150), factor)
        elif t < 0.75: 
            factor = (t - 0.5) / 0.25
            top = lerp_color((60, 160, 240), (200, 80, 40), factor)
            bot = lerp_color((180, 220, 255), (255, 140, 60), factor)
            light_val = lerp_color((255, 220, 150), (180, 120, 80), factor)
        else: 
            factor = (t - 0.75) / 0.25
            top = lerp_color((200, 80, 40), (20, 30, 60), factor)
            bot = lerp_color((255, 140, 60), (10, 15, 30), factor)
            light_val = lerp_color((180, 120, 80), (50, 40, 40), factor)

        self._draw_sky_gradient(surface, top, bot)
        
        if t > 0.75 or t < 0.25:
            self._draw_stars(surface)
            self._draw_moon(surface, 200, 120)
        else:
            self._draw_sun(surface, 1060, 120, (255, 245, 200), (255, 200, 100))

        dune_color1 = lerp_color((40, 30, 20), (210, 170, 110), light_val[0]/255.0)
        dune_color2 = lerp_color((30, 20, 15), (190, 150, 90), light_val[0]/255.0)
        
        self._draw_hills(surface, dune_color1, 60, 0.8, 15, 1.2, GROUND_Y - 100)
        self._draw_hills(surface, dune_color2, 40, 1.3, 10, 0.9, GROUND_Y - 50)
        
        self._draw_ground_texture(surface, 
                                  lerp_color((20,15,10), (180, 130, 80), light_val[0]/255.0),
                                  lerp_color((15,10,5), (150, 100, 60), light_val[0]/255.0),
                                  lerp_color((30,20,15), (220, 180, 120), light_val[0]/255.0),
                                  lerp_color((40,25,20), (240, 200, 140), light_val[0]/255.0))

    def _draw_mars(self, surface):
        self._draw_sky_gradient(surface, (140, 40, 20), (200, 100, 50))
        self._draw_sun(surface, 1060, 120, (255, 180, 100), (200, 80, 20))
        self._draw_hills(surface, (120, 40, 30), 80, 1.5, 30, 0.5, GROUND_Y - 120)
        self._draw_hills(surface, (90, 20, 15), 50, 2.0, 15, 0.8, GROUND_Y - 60)
        self._draw_ground_texture(surface, (70, 20, 15), (50, 15, 10), (100, 30, 20), (130, 45, 30))


# ============================================================================
# OBSTACLE CLASSES
# ============================================================================
class Obstacle:
    def __init__(self, x, width, height, y_offset=0):
        self.x = float(x)
        self.width = width
        self.height = height
        self.y = float(GROUND_Y - height - y_offset)
        self.is_active = True

    def update(self, dt, speed):
        self.x -= speed * dt

    def get_hitbox(self):
        return pygame.Rect(int(self.x + 4), int(self.y + 4), int(self.width - 8), int(self.height - 8))

    def draw(self, surface):
        pass


class ThornBush(Obstacle):
    def draw(self, surface):
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        
        pygame.draw.ellipse(surface, (30, 60, 20), (int(self.x), int(self.y + self.height*0.3), int(self.width), int(self.height*0.7)))
        
        num_thorns = 8
        for i in range(num_thorns):
            angle = (i / num_thorns) * math.pi
            rx = center_x + math.cos(angle) * (self.width/2.5)
            ry = center_y - math.sin(angle) * (self.height/2.5)
            pygame.draw.polygon(surface, (60, 90, 40), [
                (rx, ry), (rx - 5, ry + 15), (rx + 5, ry + 15)
            ])


class BouncingObstacle(Obstacle):
    def __init__(self, x, width, height, bounce_height):
        super().__init__(x, width, height)
        self.vy = 0
        self.bounce_vel = -math.sqrt(2 * GRAVITY * bounce_height)
        self.angle = 0.0

    def update(self, dt, speed):
        super().update(dt, speed)
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        if self.y >= GROUND_Y - self.height:
            self.y = float(GROUND_Y - self.height)
            self.vy = self.bounce_vel
            
        self.angle = (self.angle + (speed / self.width) * dt * 50.0) % 360.0


class Football(BouncingObstacle):
    def __init__(self, x, width, height, bounce_height):
        super().__init__(x, width, height, bounce_height)
        self.surf = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
        rect = pygame.Rect(0, 0, int(width), int(height))
        pygame.draw.ellipse(self.surf, (139, 69, 19), rect)
        
        lace_x = width * 0.3
        lace_y = height * 0.2
        pygame.draw.line(self.surf, (255, 255, 255), (lace_x, lace_y), (width*0.7, lace_y), 2)
        for i in range(4):
            lx = lace_x + i * (width * 0.1)
            pygame.draw.line(self.surf, (255, 255, 255), (lx, lace_y - 2), (lx, lace_y + 2), 2)
            
    def draw(self, surface):
        rot_surf = pygame.transform.rotate(self.surf, self.angle)
        rot_rect = rot_surf.get_rect(center=(int(self.x + self.width/2), int(self.y + self.height/2)))
        surface.blit(rot_surf, rot_rect.topleft)


class Cactus(Obstacle):
    def draw(self, surface):
        c_green = (40, 120, 50)
        c_dark = (20, 80, 30)
        trunk_w = self.width * 0.4
        trunk_x = self.x + (self.width - trunk_w) / 2
        pygame.draw.rect(surface, c_green, (int(trunk_x), int(self.y), int(trunk_w), int(self.height)), border_radius=8)
        
        arm_w = self.width * 0.3
        arm_h = self.height * 0.4
        pygame.draw.rect(surface, c_green, (int(self.x), int(self.y + self.height*0.3), int(arm_w), int(arm_h)), border_radius=5)
        pygame.draw.rect(surface, c_green, (int(self.x + self.width - arm_w), int(self.y + self.height*0.5), int(arm_w), int(arm_h)), border_radius=5)
        
        for i in range(5):
            py = self.y + 10 + i * (self.height / 5)
            pygame.draw.line(surface, c_dark, (trunk_x - 2, py), (trunk_x + 2, py), 1)
            pygame.draw.line(surface, c_dark, (trunk_x + trunk_w - 2, py + 5), (trunk_x + trunk_w + 2, py + 5), 1)


class CheeseBall(BouncingObstacle):
    def __init__(self, x, width, height, bounce_height):
        super().__init__(x, width, height, bounce_height)
        self.surf = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
        cx, cy = int(width/2), int(height/2)
        radius = int(width/2)
        pygame.draw.circle(self.surf, (255, 200, 50), (cx, cy), radius)
        
        holes = [
            (cx - radius*0.3, cy - radius*0.3, radius*0.2),
            (cx + radius*0.4, cy - radius*0.1, radius*0.25),
            (cx - radius*0.1, cy + radius*0.4, radius*0.15)
        ]
        for hx, hy, hr in holes:
            pygame.draw.circle(self.surf, (220, 160, 30), (int(hx), int(hy)), int(hr))
            
    def draw(self, surface):
        rot_surf = pygame.transform.rotate(self.surf, self.angle)
        rot_rect = rot_surf.get_rect(center=(int(self.x + self.width/2), int(self.y + self.height/2)))
        surface.blit(rot_surf, rot_rect.topleft)


class MetalScrap(Obstacle):
    def draw(self, surface):
        colors = [(100, 100, 100), (150, 150, 150), (80, 80, 80)]
        for i in range(5):
            px = self.x + random.uniform(0, self.width*0.6)
            py = self.y + random.uniform(0, self.height*0.6)
            pw = random.uniform(self.width*0.2, self.width*0.6)
            ph = random.uniform(self.height*0.2, self.height*0.6)
            pygame.draw.rect(surface, random.choice(colors), (int(px), int(py), int(pw), int(ph)))
            
        pygame.draw.line(surface, (200, 50, 50), (self.x, self.y), (self.x + self.width, self.y + self.height), 3)
        pygame.draw.line(surface, (200, 50, 50), (self.x + self.width, self.y), (self.x, self.y + self.height), 3)


# ============================================================================
# OBSTACLE MANAGER (Difficulty & Spawning)
# ============================================================================
class ObstacleManager:
    def __init__(self):
        self.obstacles = []
        self.time_since_last_spawn = 0.0
        self.survival_time = 0.0
        self.has_started = False
        
        self.min_interval = 0.5
        self.max_interval = 2.5
        self.difficulty_ramp_time = 90.0 # seconds to reach max difficulty

    def reset(self):
        self.obstacles.clear()
        self.time_since_last_spawn = 0.0
        self.survival_time = 0.0
        self.has_started = False

    def get_current_interval(self):
        progress = min(1.0, self.survival_time / self.difficulty_ramp_time)
        return self.max_interval - (self.max_interval - self.min_interval) * progress

    def spawn_static_obstacle(self, x, mode, char_height):
        if mode in (GameMode.DAY, GameMode.NIGHT):
            w, h = char_height * 0.8, char_height
            self.obstacles.append(ThornBush(x, w, h))
        elif mode == GameMode.DESERT:
            h = random.uniform(0.75 * char_height, 1.25 * char_height)
            w = char_height * 0.5
            self.obstacles.append(Cactus(x, w, h))
        elif mode == GameMode.MARS:
            w, h = char_height, char_height
            self.obstacles.append(MetalScrap(x, w, h))

    def spawn_single_obstacle(self, x, mode, char_height):
        if mode in (GameMode.DAY, GameMode.NIGHT):
            if random.choice([True, False]):
                self.spawn_static_obstacle(x, mode, char_height)
            else:
                w, h = (char_height / 3) * 1.5, char_height / 3
                self.obstacles.append(Football(x, w, h, bounce_height=char_height))
        elif mode == GameMode.DESERT:
            self.spawn_static_obstacle(x, mode, char_height)
        elif mode == GameMode.MARS:
            if random.choice([True, False]):
                w, h = char_height / 3, char_height / 3
                self.obstacles.append(CheeseBall(x, w, h, bounce_height=char_height))
            else:
                self.spawn_static_obstacle(x, mode, char_height)

    def spawn_pattern(self, speed, mode, char_height):
        spawn_x = SCREEN_WIDTH + 50
        
        # Calculate safe jump distance based on physics variables
        jump_time = 2 * abs(JUMP_STRENGTH) / GRAVITY
        jump_dist = speed * jump_time
        safe_gap = jump_dist + 50 # Add generous padding for player reaction/landing time
        
        # Decide if we throw a multi-obstacle cluster
        is_tight_pattern = random.random() < 0.2 and self.get_current_interval() < 1.5
        
        # Ensure we never spawn physically impossible sequences
        if self.obstacles:
            last_obs = self.obstacles[-1]
            dist_to_last = spawn_x - (last_obs.x + last_obs.width)
            
            if dist_to_last < safe_gap:
                spawn_x = last_obs.x + last_obs.width + safe_gap
                
        if is_tight_pattern:
            self.spawn_static_obstacle(spawn_x, mode, char_height)
            tight_gap = 25
            last_w = self.obstacles[-1].width
            self.spawn_static_obstacle(spawn_x + last_w + tight_gap, mode, char_height)
        else:
            self.spawn_single_obstacle(spawn_x, mode, char_height)

    def update(self, dt, speed, mode, char_height):
        self.survival_time += dt
        
        if not self.has_started:
            if self.survival_time >= 2.5: # Initial wait exactly approximately 2.5 seconds
                self.has_started = True
                self.spawn_pattern(speed, mode, char_height)
                self.time_since_last_spawn = 0.0
        else:
            self.time_since_last_spawn += dt
            interval = self.get_current_interval()
            
            if self.time_since_last_spawn >= interval:
                self.spawn_pattern(speed, mode, char_height)
                self.time_since_last_spawn = 0.0

        for obs in self.obstacles:
            obs.update(dt, speed)
            
        self.obstacles = [obs for obs in self.obstacles if obs.x + obs.width > -100]

    def check_collision(self, player_hitbox):
        for obs in self.obstacles:
            if player_hitbox.colliderect(obs.get_hitbox()):
                return True
        return False

    def draw(self, surface, debug_hitboxes=False):
        for obs in self.obstacles:
            obs.draw(surface)
            if debug_hitboxes:
                pygame.draw.rect(surface, (0, 255, 255), obs.get_hitbox(), 2)


# ============================================================================
# UI & HUD RENDERING HELPERS
# ============================================================================
class UIRenderer:
    def __init__(self):
        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", 52, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", 30, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 20, bold=False)
        self.font_mono = pygame.font.SysFont("Courier New", 26, bold=True)

    def draw_text_with_shadow(self, surface, text, font, color, center_pos, offset=(2, 2)):
        txt_surf = font.render(text, True, color)
        rect = txt_surf.get_rect(center=center_pos)
        sh_surf = font.render(text, True, (20, 20, 20))
        surface.blit(sh_surf, (rect.x + offset[0], rect.y + offset[1]))
        surface.blit(txt_surf, rect)
        return rect

    def draw_card(self, surface, rect, is_active=False, is_selected=False):
        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg_alpha = 220 if is_selected else (190 if is_active else 150)
        card_color = (*COLOR_PANEL_BG[:3], bg_alpha)
        pygame.draw.rect(card_surf, card_color, (0, 0, rect.width, rect.height), border_radius=12)

        border_color = COLOR_PANEL_HIGHLIGHT if is_selected else (COLOR_ACCENT_GOLD if is_active else COLOR_PANEL_BORDER)
        border_width = 3 if is_selected else 1
        pygame.draw.rect(card_surf, border_color, (0, 0, rect.width, rect.height), width=border_width, border_radius=12)
        surface.blit(card_surf, rect.topleft)


# ============================================================================
# CORE GAME CLASS
# ============================================================================
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Endless Runner - Gameplay Loop & Difficulty")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_running = True

        self.state = GameState.MAIN_MENU
        self.selected_character = CharacterType.CLASSIC
        self.selected_mode = GameMode.DAY

        self.ui = UIRenderer()
        self.bg = BackgroundSystem()
        self.player = Player(x=190, char_type=self.selected_character)
        self.obstacle_mgr = ObstacleManager()

        self.survival_time = 0.0
        self.score = 0

        self.menu_options = ["PLAY", "CHARACTER", "GAME MODE", "QUIT"]
        self.menu_index = 0

        self.char_list = CharacterType.ALL
        self.char_select_index = 0

        self.mode_list = GameMode.ALL
        self.mode_select_index = 0

        self.debug_hitboxes = False

    def start_game(self):
        self.survival_time = 0.0
        self.score = 0
        self.player.set_character(self.selected_character)
        self.player.reset()
        self.obstacle_mgr.reset()
        self.state = GameState.PLAYING

    def trigger_game_over(self):
        self.state = GameState.GAME_OVER

    def restart_game(self):
        self.start_game()

    def run(self):
        while self.is_running:
            raw_dt = self.clock.tick(FPS) / 1000.0
            dt = min(raw_dt, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    self.debug_hitboxes = not self.debug_hitboxes
                if self.state == GameState.MAIN_MENU:
                    self._handle_main_menu_input(event.key)
                elif self.state == GameState.CHAR_SELECT:
                    self._handle_char_select_input(event.key)
                elif self.state == GameState.MODE_SELECT:
                    self._handle_mode_select_input(event.key)
                elif self.state == GameState.PLAYING:
                    self._handle_playing_input(event.key)
                elif self.state == GameState.GAME_OVER:
                    self._handle_game_over_input(event.key)

    def _handle_main_menu_input(self, key):
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            choice = self.menu_options[self.menu_index]
            if choice == "PLAY":
                self.start_game()
            elif choice == "CHARACTER":
                self.char_select_index = self.char_list.index(self.selected_character)
                self.state = GameState.CHAR_SELECT
            elif choice == "GAME MODE":
                self.mode_select_index = self.mode_list.index(self.selected_mode)
                self.state = GameState.MODE_SELECT
            elif choice == "QUIT":
                self.is_running = False
        elif key == pygame.K_ESCAPE:
            self.is_running = False

    def _handle_char_select_input(self, key):
        if key in (pygame.K_LEFT, pygame.K_a):
            self.char_select_index = (self.char_select_index - 1) % len(self.char_list)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.char_select_index = (self.char_select_index + 1) % len(self.char_list)
        elif key == pygame.K_1: self.char_select_index = 0
        elif key == pygame.K_2: self.char_select_index = 1
        elif key == pygame.K_3: self.char_select_index = 2
        elif key == pygame.K_4: self.char_select_index = 3
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.selected_character = self.char_list[self.char_select_index]
            self.player.set_character(self.selected_character)
            self.state = GameState.MAIN_MENU
        elif key == pygame.K_ESCAPE:
            self.state = GameState.MAIN_MENU

    def _handle_mode_select_input(self, key):
        if key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
            self.mode_select_index = (self.mode_select_index - 1) % len(self.mode_list)
        elif key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
            self.mode_select_index = (self.mode_select_index + 1) % len(self.mode_list)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.selected_mode = self.mode_list[self.mode_select_index]
            self.state = GameState.MAIN_MENU
        elif key == pygame.K_ESCAPE:
            self.state = GameState.MAIN_MENU

    def _handle_playing_input(self, key):
        if key == pygame.K_SPACE:
            self.player.jump()
        elif key == pygame.K_ESCAPE:
            self.state = GameState.MAIN_MENU

    def _handle_game_over_input(self, key):
        if key == pygame.K_r:
            self.restart_game()
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
            self.state = GameState.MAIN_MENU

    def update(self, dt):
        current_speed = PLAYER_SPEED

        if self.state == GameState.PLAYING:
            self.survival_time += dt
            # Exact mapping: 1 point per 0.01s -> 100 points per 1.0s
            self.score = int(self.survival_time * 100)

            self.player.update(dt)
            self.bg.update(dt, current_speed, self.selected_mode)
            
            self.obstacle_mgr.update(dt, current_speed, self.selected_mode, self.player.height)
            if self.obstacle_mgr.check_collision(self.player.get_hitbox()):
                self.trigger_game_over()
                
        elif self.state == GameState.GAME_OVER:
            # Player / Obstacles freeze immediately (no update logic called).
            # Score accumulation stops (since survival_time doesn't increase).
            # We still update the background with 0 speed, so Time of Day cycles but terrain is still!
            self.bg.update(dt, 0.0, self.selected_mode)

        elif self.state in (GameState.MAIN_MENU, GameState.CHAR_SELECT, GameState.MODE_SELECT):
            self.bg.update(dt, current_speed * 0.4, self.selected_mode)
            self.player.anim_timer += dt

    def draw(self):
        self.bg.draw(self.screen)

        if self.state == GameState.PLAYING:
            self._draw_playing()
        elif self.state == GameState.MAIN_MENU:
            self._draw_main_menu()
        elif self.state == GameState.CHAR_SELECT:
            self._draw_char_select()
        elif self.state == GameState.MODE_SELECT:
            self._draw_mode_select()
        elif self.state == GameState.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

        pygame.display.flip()

    def _draw_playing(self):
        self.obstacle_mgr.draw(self.screen, self.debug_hitboxes)
        self.player.draw(self.screen, self.debug_hitboxes)

        score_str = f"SCORE: {self.score:06d}"
        badge_w, badge_h = 240, 50
        badge_rect = pygame.Rect(SCREEN_WIDTH - badge_w - 30, 24, badge_w, badge_h)
        self.ui.draw_card(self.screen, badge_rect, is_selected=True)
        self.ui.draw_text_with_shadow(self.screen, score_str, self.ui.font_mono, COLOR_ACCENT_GOLD, badge_rect.center)

        left_w, left_h = 280, 50
        left_rect = pygame.Rect(30, 24, left_w, left_h)
        self.ui.draw_card(self.screen, left_rect)
        info_str = f"{self.selected_character}  |  {self.selected_mode}"
        self.ui.draw_text_with_shadow(self.screen, info_str, self.ui.font_small, COLOR_TEXT_PRIMARY, left_rect.center)

        hint_text = "SPACE: Jump   |   ESC: Menu"
        hint_surf = self.ui.font_small.render(hint_text, True, (240, 240, 240))
        self.screen.blit(hint_surf, (30, SCREEN_HEIGHT - 32))

    def _draw_main_menu(self):
        dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((15, 23, 42, 130))
        self.screen.blit(dim_surf, (0, 0))

        title_y = 150
        self.ui.draw_text_with_shadow(self.screen, "ENDLESS RUNNER", self.ui.font_large, COLOR_ACCENT_GOLD, (SCREEN_WIDTH // 2, title_y), offset=(3, 3))
        self.ui.draw_text_with_shadow(self.screen, "CHUNK 3: GAMEPLAY LOOP & DIFFICULTY", self.ui.font_small, COLOR_ACCENT_CYAN, (SCREEN_WIDTH // 2, title_y + 44))

        start_y, item_h = 280, 60
        for i, opt in enumerate(self.menu_options):
            is_selected = (i == self.menu_index)
            cy = start_y + (i * item_h)
            card_rect = pygame.Rect(SCREEN_WIDTH // 2 - 170, cy - 25, 340, 50)
            self.ui.draw_card(self.screen, card_rect, is_selected=is_selected)

            prefix = "> " if is_selected else "  "
            suffix = " <" if is_selected else "  "
            display_text = f"{prefix}{opt}{suffix}"
            text_color = COLOR_ACCENT_GOLD if is_selected else COLOR_TEXT_PRIMARY
            self.ui.draw_text_with_shadow(self.screen, display_text, self.ui.font_medium, text_color, card_rect.center)

        nav_info = "[UP/DOWN or W/S] Navigate    [ENTER] Select    [ESC] Quit"
        self.ui.draw_text_with_shadow(self.screen, nav_info, self.ui.font_small, COLOR_TEXT_MUTED, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 45))

    def _draw_char_select(self):
        dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((15, 23, 42, 175))
        self.screen.blit(dim_surf, (0, 0))

        self.ui.draw_text_with_shadow(self.screen, "SELECT YOUR CHARACTER", self.ui.font_large, COLOR_WHITE, (SCREEN_WIDTH // 2, 70))

        card_w, card_h = 260, 90
        start_x = (SCREEN_WIDTH - (len(self.char_list) * (card_w + 20) - 20)) // 2
        card_y = 130

        for i, c_name in enumerate(self.char_list):
            is_cursor = (i == self.char_select_index)
            is_active = (c_name == self.selected_character)
            cx = start_x + (i * (card_w + 20))
            rect = pygame.Rect(cx, card_y, card_w, card_h)
            self.ui.draw_card(self.screen, rect, is_active=is_active, is_selected=is_cursor)

            self.ui.draw_text_with_shadow(self.screen, f"[{i + 1}] {c_name}", self.ui.font_medium, COLOR_ACCENT_GOLD if is_cursor else COLOR_TEXT_PRIMARY, (rect.centerx, rect.centery - 10))

            status_text = "CURRENT" if is_active else ("PRESS ENTER" if is_cursor else "")
            if status_text:
                self.ui.draw_text_with_shadow(self.screen, status_text, self.ui.font_small, COLOR_ACCENT_CYAN if is_cursor else COLOR_TEXT_MUTED, (rect.centerx, rect.centery + 22))

        focused_char = self.char_list[self.char_select_index]
        info = CharacterType.INFO[focused_char]
        preview_card = pygame.Rect(SCREEN_WIDTH // 2 - 320, 260, 640, 360)
        self.ui.draw_card(self.screen, preview_card, is_selected=True)

        self.ui.draw_text_with_shadow(self.screen, info["title"], self.ui.font_large, COLOR_ACCENT_GOLD, (SCREEN_WIDTH // 2, 305))
        self.ui.draw_text_with_shadow(self.screen, info["desc"], self.ui.font_small, COLOR_TEXT_PRIMARY, (SCREEN_WIDTH // 2, 350))

        pedestal_y = 540
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (preview_card.left + 50, pedestal_y), (preview_card.right - 50, pedestal_y), 3)

        prev_player = Player(char_type=focused_char)
        prev_player.anim_timer = self.player.anim_timer
        prev_player.draw_preview(self.screen, SCREEN_WIDTH // 2, pedestal_y - 45, scale=1.65)

        inst_text = "[A/D or LEFT/RIGHT or 1-4] Choose    [ENTER] Confirm    [ESC] Back"
        self.ui.draw_text_with_shadow(self.screen, inst_text, self.ui.font_small, COLOR_TEXT_MUTED, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35))

    def _draw_mode_select(self):
        dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((15, 23, 42, 175))
        self.screen.blit(dim_surf, (0, 0))

        self.ui.draw_text_with_shadow(self.screen, "SELECT GAME MODE", self.ui.font_large, COLOR_WHITE, (SCREEN_WIDTH // 2, 80))

        card_w, card_h = 240, 300
        start_x = (SCREEN_WIDTH - (len(self.mode_list) * (card_w + 20) - 20)) // 2
        card_y = 170

        for i, m_name in enumerate(self.mode_list):
            is_cursor = (i == self.mode_select_index)
            is_active = (m_name == self.selected_mode)
            cfg = GameMode.INFO[m_name]
            
            cx = start_x + (i * (card_w + 20))
            rect = pygame.Rect(cx, card_y, card_w, card_h)
            self.ui.draw_card(self.screen, rect, is_active=is_active, is_selected=is_cursor)

            title_color = cfg["color"] if is_cursor else COLOR_TEXT_PRIMARY
            self.ui.draw_text_with_shadow(self.screen, m_name, self.ui.font_large, title_color, (rect.centerx, rect.top + 60))

            if is_active:
                badge_rect = pygame.Rect(rect.centerx - 50, rect.top + 110, 100, 28)
                pygame.draw.rect(self.screen, COLOR_ACCENT_GOLD, badge_rect, border_radius=6)
                b_surf = self.ui.font_small.render("ACTIVE", True, COLOR_DARK_SLATE)
                self.screen.blit(b_surf, b_surf.get_rect(center=badge_rect.center))

            words = cfg["desc"].split(' ')
            lines = []
            line = ""
            for w in words:
                if len(line) + len(w) > 20:
                    lines.append(line)
                    line = w + " "
                else:
                    line += w + " "
            lines.append(line)
            
            for j, l in enumerate(lines):
                self.ui.draw_text_with_shadow(self.screen, l.strip(), self.ui.font_small, COLOR_TEXT_MUTED, (rect.centerx, rect.top + 180 + j*25))

        inst_text = "[LEFT/RIGHT or A/D] Navigate    [ENTER] Select    [ESC] Back"
        self.ui.draw_text_with_shadow(self.screen, inst_text, self.ui.font_small, COLOR_TEXT_MUTED, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35))

    def _draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 12, 16, 210))
        self.screen.blit(overlay, (0, 0))

        self.ui.draw_text_with_shadow(self.screen, "GAME OVER", self.ui.font_large, COLOR_ACCENT_RED, (SCREEN_WIDTH // 2, 140), offset=(4, 4))

        card_w, card_h = 520, 270
        card_rect = pygame.Rect(SCREEN_WIDTH // 2 - (card_w // 2), 210, card_w, card_h)
        self.ui.draw_card(self.screen, card_rect, is_selected=True)

        self.ui.draw_text_with_shadow(self.screen, f"FINAL SCORE: {self.score:06d}", self.ui.font_large, COLOR_ACCENT_GOLD, (card_rect.centerx, card_rect.top + 55))
        self.ui.draw_text_with_shadow(self.screen, f"SURVIVAL TIME: {self.survival_time:.2f}s", self.ui.font_medium, COLOR_TEXT_PRIMARY, (card_rect.centerx, card_rect.top + 115))
        self.ui.draw_text_with_shadow(self.screen, f"CHARACTER: {self.selected_character}", self.ui.font_medium, COLOR_ACCENT_CYAN, (card_rect.centerx, card_rect.top + 165))
        self.ui.draw_text_with_shadow(self.screen, f"GAME MODE: {self.selected_mode}", self.ui.font_medium, COLOR_TEXT_MUTED, (card_rect.centerx, card_rect.top + 215))

        opt_y = 540
        self.ui.draw_text_with_shadow(self.screen, "[ R ]  RESTART GAME", self.ui.font_medium, COLOR_ACCENT_GOLD, (SCREEN_WIDTH // 2, opt_y))
        self.ui.draw_text_with_shadow(self.screen, "[ ENTER ]  RETURN TO MENU", self.ui.font_medium, COLOR_WHITE, (SCREEN_WIDTH // 2, opt_y + 50))


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    game = Game()
    game.run()
