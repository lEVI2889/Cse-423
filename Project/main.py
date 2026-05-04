import sys
import math
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *


def enforce_boundaries(x, z, player_radius):
    max_distance = arena_radius - player_radius
    distance = math.sqrt(x ** 2 + z ** 2)
    if distance > max_distance:
        ratio = max_distance / distance
        x *= ratio
        z *= ratio
    return x, z


def applying_rng_speeds(players_array):
    for p in players_array:
        p['speed'] = random.uniform(0.04, 0.06)


def compPlayer_to_target(p, target_x, target_z, terrain_mult=1.0):
    dx = target_x - p['x']
    dz = target_z - p['z']
    dist = math.sqrt(dx ** 2 + dz ** 2)
    if dist > 0.1:
        actual_speed = p['speed'] * terrain_mult
        p['x'] += (dx / dist) * actual_speed
        p['z'] += (dz / dist) * actual_speed
        p['facing'] = math.degrees(math.atan2(dx, dz))


def ball_collision_check(player_x, player_z, player_radius, ball_radius):
    distance = math.sqrt((player_x - 0.0) ** 2 + (player_z - 0.0) ** 2)
    return distance <= (player_radius + ball_radius)


def terrain_multiplier(px, pz, qs_x, qs_z, qs_radius):
    dist = math.sqrt((px - qs_x) ** 2 + (pz - qs_z) ** 2)
    if dist <= qs_radius:
        return 0.3
    return 1.0


def item_collision_checker(px, pz, item_x, item_z, item_radius, player_radius=1.0):
    dist = math.sqrt((px - item_x) ** 2 + (pz - item_z) ** 2)
    return dist <= (item_radius + player_radius)


def getSmartWaypoint(px, pz, target_x, target_z, qs_x, qs_z, qs_radius, base_speed):
    line_dist = math.sqrt((target_x - px) ** 2 + (target_z - pz) ** 2)
    if line_dist == 0:
        return target_x, target_z
    t = ((qs_x - px) * (target_x - px) + (qs_z - pz) * (target_z - pz)) / (line_dist ** 2)
    if 0 < t < 1:
        closest_x = px + t * (target_x - px)
        closest_z = pz + t * (target_z - pz)
        dist_to_path = math.sqrt((qs_x - closest_x) ** 2 + (qs_z - closest_z) ** 2)
        if dist_to_path < qs_radius:
            dist_inside_qs = 2 * math.sqrt(qs_radius ** 2 - dist_to_path ** 2)
            dist_outside_qs = line_dist - dist_inside_qs
            time_straight = (dist_outside_qs / base_speed) + (dist_inside_qs / (base_speed * 0.3))
            nx = -(target_z - pz) / line_dist
            nz = (target_x - px) / line_dist
            waypoint_radius = qs_radius + 1.5
            wp1_x = qs_x + nx * waypoint_radius
            wp1_z = qs_z + nz * waypoint_radius
            wp2_x = qs_x - nx * waypoint_radius
            wp2_z = qs_z - nz * waypoint_radius
            dist1 = math.sqrt((wp1_x - px) ** 2 + (wp1_z - pz) ** 2)
            dist2 = math.sqrt((wp2_x - px) ** 2 + (wp2_z - pz) ** 2)
            bypass_x, bypass_z = (wp1_x, wp1_z) if dist1 < dist2 else (wp2_x, wp2_z)
            dist_bypass = math.sqrt((bypass_x - px) ** 2 + (bypass_z - pz) ** 2) + math.sqrt(
                (target_x - bypass_x) ** 2 + (target_z - bypass_z) ** 2)
            time_bypass = dist_bypass / base_speed
            if time_bypass < time_straight:
                return bypass_x, bypass_z
    return target_x, target_z


def evasion_target_seeker(px, pz, goal_x, goal_z, players_list, carrier_id, danger_radius=6.0):
    dx = goal_x - px
    dz = goal_z - pz
    repel_x = 0.0
    repel_z = 0.0
    for p in players_list:
        if p['id'] != carrier_id:
            dist = math.sqrt((p['x'] - px) ** 2 + (p['z'] - pz) ** 2)
            if 0 < dist < danger_radius:
                force = (danger_radius - dist) / danger_radius
                repel_x += ((px - p['x']) / dist) * force * 15.0
                repel_z += ((pz - p['z']) / dist) * force * 15.0
    return px + dx + repel_x, pz + dz + repel_z


arena_radius = 25.0
ball_radius = 1.0


def draw_arena():
    stripe_width = 2.5
    step = 0.25
    z = -arena_radius
    glBegin(GL_QUADS)
    while z < arena_radius:
        z_next = z + step
        if z_next > arena_radius:
            z_next = arena_radius
        stripe_index = int((z + arena_radius + 0.001) / stripe_width)
        if stripe_index % 2 == 0:
            glColor3f(0.1, 0.38, 0.1)
        else:
            glColor3f(0.15, 0.45, 0.15)
        x1 = math.sqrt(max(0, arena_radius ** 2 - z ** 2))
        x2 = math.sqrt(max(0, arena_radius ** 2 - z_next ** 2))
        glVertex3f(-x1, 0.0, z)
        glVertex3f(x1, 0.0, z)
        glVertex3f(x2, 0.0, z_next)
        glVertex3f(-x2, 0.0, z_next)
        z = z_next
    glEnd()

    boundary_radius = arena_radius - 1.5
    glLineWidth(3.0)
    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_LINE_LOOP)
    for i in range(360):
        theta = i * math.pi / 180.0
        x = boundary_radius * math.cos(theta)
        z_pos = boundary_radius * math.sin(theta)
        glVertex3f(x, 0.01, z_pos)
    glEnd()

    glBegin(GL_LINE_LOOP)
    for i in range(360):
        theta = i * math.pi / 180.0
        x = 5.0 * math.cos(theta)
        z_pos = 5.0 * math.sin(theta)
        glVertex3f(x, 0.01, z_pos)
    glEnd()

    glBegin(GL_LINES)
    glVertex3f(-boundary_radius, 0.01, 0.0)
    glVertex3f(boundary_radius, 0.01, 0.0)
    glEnd()
    glLineWidth(1.0)
    glPushMatrix()
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    quadric = gluNewQuadric()

    glColor3f(0.1, 0.08, 0.12)
    glTranslatef(0.0, 0.0, -8.0)
    gluCylinder(quadric, arena_radius, arena_radius, 8.0, 64, 1)
    gluDisk(quadric, 0.0, arena_radius, 64, 1)

    glTranslatef(0.0, 0.0, 8.0)
    glColor3f(0.55, 0.27, 0.07)
    gluCylinder(quadric, arena_radius, arena_radius, 2.5, 64, 1)

    glTranslatef(0.0, 0.0, 2.5)
    glColor3f(0.65, 0.35, 0.15)
    gluDisk(quadric, arena_radius - 0.8, arena_radius + 0.5, 64, 1)

    gluDeleteQuadric(quadric)
    glPopMatrix()


def draw_ball():
    glColor3f(1.0, 1.0, 1.0)
    glPushMatrix()
    glTranslatef(0.0, ball_radius, 0.0)
    glutSolidSphere(ball_radius, 20, 20)
    glPopMatrix()


def draw_player(x, z, color, limb_angle=0.0, y_angle=0.0, is_carrier=False, is_human=False):
    glPushMatrix()
    glTranslatef(x, 1.2, z)
    glRotatef(y_angle, 0.0, 1.0, 0.0)

    if is_carrier:
        glColor3f(1.0, 0.8, 0.0)
        glPushMatrix()
        glTranslatef(0.0, -1.15, 0.0)
        glRotatef(-90.0, 1.0, 0.0, 0.0)
        quadric = gluNewQuadric()
        gluDisk(quadric, 0.8, 1.4, 32, 1)
        gluDeleteQuadric(quadric)
        glPopMatrix()

    glColor3f(*color)
    glPushMatrix()
    glScalef(0.6, 1.0, 0.4)
    glutSolidCube(1.0)
    glPopMatrix()

    glColor3f(0.1, 0.1, 0.1)
    glPushMatrix()
    glTranslatef(0.0, 0.8, 0.0)
    glutSolidSphere(0.35, 32, 32)
    glPopMatrix()

    if is_human:
        glColor3f(1.0, 1.0, 1.0)
        glPushMatrix()
        bob_offset = abs(limb_angle) / 150.0
        glTranslatef(0.0, 2.3 + bob_offset, 0.0)
        glRotatef(90.0, 1.0, 0.0, 0.0)
        quadric = gluNewQuadric()
        gluCylinder(quadric, 0.6, 0.0, 0.8, 32, 1)
        gluDeleteQuadric(quadric)
        glPopMatrix()

    beige = (0.96, 0.87, 0.70)
    glColor3f(*beige)

    glPushMatrix()
    glTranslatef(-0.4, 0.4, 0.0)
    glRotatef(-limb_angle, 1.0, 0.0, 0.0)
    glTranslatef(0.0, -0.4, 0.0)
    glScalef(0.2, 0.8, 0.2)
    glutSolidCube(1.0)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0.4, 0.4, 0.0)
    glRotatef(limb_angle, 1.0, 0.0, 0.0)
    glTranslatef(0.0, -0.4, 0.0)
    glScalef(0.2, 0.8, 0.2)
    glutSolidCube(1.0)
    glPopMatrix()

    glColor3f(*color)

    glPushMatrix()
    glTranslatef(-0.2, -0.5, 0.0)
    glRotatef(limb_angle, 1.0, 0.0, 0.0)
    glTranslatef(0.0, -0.5, 0.0)
    glScalef(0.25, 1.0, 0.25)
    glutSolidCube(1.0)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0.2, -0.5, 0.0)
    glRotatef(-limb_angle, 1.0, 0.0, 0.0)
    glTranslatef(0.0, -0.5, 0.0)
    glScalef(0.25, 1.0, 0.25)
    glutSolidCube(1.0)
    glPopMatrix()

    if is_carrier:
        glColor3f(0.65, 0.65, 0.65)
        glPushMatrix()
        bounce = abs(limb_angle) / 45.0
        glTranslatef(0.0, -0.95 + (bounce * 0.2), 0.8)
        glutSolidSphere(0.25, 32, 32)
        glPopMatrix()

    glPopMatrix()


def draw_text(text, x, y):
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(1.0, 1.0, 1.0)
    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)


def draw_goalpost(x, z):
    glColor3f(0.9, 0.9, 0.9)
    glPushMatrix()
    glTranslatef(x, 0.0, z)
    angle = math.degrees(math.atan2(-x, -z))
    glRotatef(angle, 0.0, 1.0, 0.0)
    quadric = gluNewQuadric()

    glPushMatrix()
    glTranslatef(-3.0, 0.0, 0.0)
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    gluCylinder(quadric, 0.3, 0.3, 5.0, 32, 1)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(3.0, 0.0, 0.0)
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    gluCylinder(quadric, 0.3, 0.3, 5.0, 32, 1)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-3.15, 4.85, 0.0)
    glRotatef(90.0, 0.0, 1.0, 0.0)
    gluCylinder(quadric, 0.3, 0.3, 6.3, 32, 1)
    glPopMatrix()

    glColor3f(0.5, 0.5, 0.5)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex3f(-3.0, 4.85, 0.0)
    glVertex3f(-3.0, 0.0, 3.0)
    glVertex3f(3.0, 4.85, 0.0)
    glVertex3f(3.0, 0.0, 3.0)
    glVertex3f(-3.0, 0.0, 3.0)
    glVertex3f(3.0, 0.0, 3.0)
    glEnd()
    glLineWidth(1.0)

    gluDeleteQuadric(quadric)
    glPopMatrix()


def speed_boost_cube(x, z, rotation_angle):
    glPushMatrix()
    glTranslatef(x, 2.0, z)
    glRotatef(rotation_angle, 0.5, 1.0, 0.5)
    glScalef(1.4, 1.4, 1.4)

    glColor3f(1.0, 0.8, 0.0)
    glutSolidSphere(0.4, 16, 16)

    glColor3f(1.0, 1.0, 0.2)
    glLineWidth(2.0)
    glutWireCube(1.0)
    glLineWidth(1.0)

    glPopMatrix()


def ghost_cloak_cube(x, z, rotation_angle):
    glColor3f(0.8, 0.8, 0.9)
    glPushMatrix()
    glTranslatef(x, 2.0, z)
    glRotatef(rotation_angle, 0.0, 1.0, 0.0)
    glRotatef(45.0, 1.0, 0.0, 0.0)
    glutSolidCube(1.0)
    glPopMatrix()


def quicksandCircle(x, z, radius):
    glColor3f(0.4, 0.25, 0.1)
    glPushMatrix()
    glTranslatef(x, 0.01, z)
    glRotatef(-90.0, 1.0, 0.0, 0.0)
    quadric = gluNewQuadric()
    gluDisk(quadric, 0.0, radius, 32, 1)
    gluDeleteQuadric(quadric)
    glPopMatrix()


def boulderRoomba(x, z, radius):
    glColor3f(0.4, 0.4, 0.45)
    glPushMatrix()
    glTranslatef(x, radius, z)
    glutSolidSphere(radius, 32, 32)
    glPopMatrix()


window_width, window_height = 800, 800
frame_count = 0
game_state = "COUNTDOWN"
ball_carrier_id = None
camera_mode = 1

keys = {'w': False, 'a': False, 's': False, 'd': False}

goalpost = {"active": False, "x": 0.0, "z": 0.0, "radius": 3.5}
quicksand = {"active": False, "x": -10.0, "z": -10.0, "radius": 5.0}
ghost_cloak = {"active": False, "x": 0.0, "z": 0.0, "angle": 0.0, "radius": 1.0}
speed_boosts = [
    {"active": False, "x": 0.0, "z": 0.0, "angle": 0.0, "radius": 1.0},
    {"active": False, "x": 0.0, "z": 0.0, "angle": 0.0, "radius": 1.0},
    {"active": False, "x": 0.0, "z": 0.0, "angle": 0.0, "radius": 1.0}
]
roombas = [
    {"active": False, "x": 0.0, "z": 0.0, "dx": 0.0, "dz": 0.0, "radius": 1.0, "speed": 0.2},
    {"active": False, "x": 0.0, "z": 0.0, "dx": 0.0, "dz": 0.0, "radius": 1.0, "speed": 0.2},
    {"active": False, "x": 0.0, "z": 0.0, "dx": 0.0, "dz": 0.0, "radius": 1.0, "speed": 0.2}
]

current_round = 1
max_rounds = 5
scores = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
tackles = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
invincibility_frames = 0
round_winner_text = ""


def reset_match():
    global current_round, scores, tackles, round_winner_text
    current_round = 1
    scores = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    tackles = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    round_winner_text = ""
    reset_round()


def reset_round():
    global game_state, frame_count, ball_carrier_id, goalpost, quicksand
    global arena_radius, spawn_radius, roombas

    game_state = "COUNTDOWN"
    frame_count = 0
    ball_carrier_id = None
    goalpost['active'] = False
    quicksand['active'] = False
    ghost_cloak['active'] = False
    for b in speed_boosts:
        b['active'] = False

    if current_round <= 3:
        arena_radius = 25.0
        spawn_radius = 23.0
    elif current_round == 4:
        arena_radius = 18.0
        spawn_radius = 16.0
    elif current_round == 5:
        arena_radius = 12.0
        spawn_radius = 10.0

    for r in roombas:
        r['active'] = False

    if current_round == 2 or current_round == 3:
        num_roombas = 2 if current_round == 2 else 3
        for i in range(num_roombas):
            roombas[i]['active'] = True
            roombas[i]['x'] = random.uniform(-5.0, 5.0)
            roombas[i]['z'] = random.uniform(-5.0, 5.0)
            angle = random.uniform(0, math.pi * 2)
            roombas[i]['dx'] = math.cos(angle) * roombas[i]['speed']
            roombas[i]['dz'] = math.sin(angle) * roombas[i]['speed']

    for i in range(5):
        angle_rad = math.radians(i * 72.0)
        start_x = spawn_radius * math.cos(angle_rad)
        start_z = spawn_radius * math.sin(angle_rad)
        players[i]['x'] = start_x
        players[i]['z'] = start_z
        players[i]['speed'] = 0.15
        players[i]['facing'] = math.degrees(math.atan2(-start_x, -start_z))


def spawn_goalpost(carrier_x, carrier_z):
    if carrier_x == 0.0 and carrier_z == 0.0:
        carrier_x = 0.01

    angle = math.atan2(carrier_z, carrier_x)
    opposite_angle = angle + math.pi
    random_offset = math.radians(random.uniform(-45.0, 45.0))
    final_angle = opposite_angle + random_offset

    goalpost['x'] = spawn_radius * math.cos(final_angle)
    goalpost['z'] = spawn_radius * math.sin(final_angle)
    goalpost['active'] = True

    quicksand['x'] = goalpost['x'] * 0.5
    quicksand['z'] = goalpost['z'] * 0.5
    quicksand['active'] = True

    qs_rad = quicksand['radius']
    boost_spawn_dist = qs_rad + 2.0

    speed_boosts[0]['x'] = quicksand['x'] + math.cos(final_angle - math.pi / 2) * boost_spawn_dist
    speed_boosts[0]['z'] = quicksand['z'] + math.sin(final_angle - math.pi / 2) * boost_spawn_dist
    speed_boosts[0]['active'] = True

    if current_round >= 3:
        ghost_cloak['x'] = quicksand['x'] + math.cos(final_angle + math.pi / 2) * boost_spawn_dist
        ghost_cloak['z'] = quicksand['z'] + math.sin(final_angle + math.pi / 2) * boost_spawn_dist
        ghost_cloak['active'] = True
    else:
        speed_boosts[1]['x'] = quicksand['x'] + math.cos(final_angle + math.pi / 2) * boost_spawn_dist
        speed_boosts[1]['z'] = quicksand['z'] + math.sin(final_angle + math.pi / 2) * boost_spawn_dist
        speed_boosts[1]['active'] = True

    if current_round <= 2:
        speed_boosts[2]['x'] = quicksand['x'] + math.cos(final_angle) * boost_spawn_dist
        speed_boosts[2]['z'] = quicksand['z'] + math.sin(final_angle) * boost_spawn_dist
        speed_boosts[2]['active'] = True


player_colors = [
    (0.2, 0.4, 1.0),
    (1.0, 0.2, 0.2),
    (1.0, 0.5, 0.0),
    (0.8, 0.2, 0.8),
    (1.0, 1.0, 0.2)
]

spawn_radius = 23.0
players = []
for i in range(5):
    angle_rad = math.radians(i * 72.0)
    start_x = spawn_radius * math.cos(angle_rad)
    start_z = spawn_radius * math.sin(angle_rad)
    initial_face_deg = math.degrees(math.atan2(-start_x, -start_z))

    players.append({
        "id": i,
        "x": start_x,
        "z": start_z,
        "color": player_colors[i],
        "speed": 0.15,
        "is_human": (i == 0),
        "facing": initial_face_deg,
        "stun_frames": 0,
        "ghost_frames": 0
    })


def keyboardListener(key, x, y):
    global camera_mode, game_state
    try:
        k = key.decode('utf-8').lower()
        if k in keys:
            keys[k] = True
        if k == '1': camera_mode = 1
        if k == '2': camera_mode = 2
        if k == '3': camera_mode = 3

        if k == 'r' and game_state == "MATCH_OVER":
            reset_match()

    except Exception:
        pass


def keyboardUpListener(key, x, y):
    try:
        k = key.decode('utf-8').lower()
        if k in keys:
            keys[k] = False
    except:
        pass


def UserControlledPlayer(terrain_mult=1.0):
    global camera_mode
    p1 = players[0]

    if p1['stun_frames'] > 0:
        return

    step = p1['speed'] * terrain_mult

    if camera_mode == 2:
        if keys['a']: p1['facing'] += 4.0
        if keys['d']: p1['facing'] -= 4.0

        rad = math.radians(p1['facing'])
        if keys['w']:
            p1['x'] += math.sin(rad) * step
            p1['z'] += math.cos(rad) * step
        if keys['s']:
            p1['x'] -= math.sin(rad) * step
            p1['z'] -= math.cos(rad) * step
    else:
        dx = 0.0
        dz = 0.0

        if keys['w']: dz -= 1.0
        if keys['s']: dz += 1.0
        if keys['a']: dx -= 1.0
        if keys['d']: dx += 1.0

        if dx != 0.0 or dz != 0.0:
            dist = math.sqrt(dx ** 2 + dz ** 2)
            p1['x'] += (dx / dist) * step
            p1['z'] += (dz / dist) * step
            p1['facing'] = math.degrees(math.atan2(dx, dz))

    p1['x'], p1['z'] = enforce_boundaries(p1['x'], p1['z'], 1.0)


def init():
    glClearColor(0.1, 0.1, 0.1, 1.0)
    glEnable(GL_DEPTH_TEST)


def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, window_width / window_height, 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode == 1:
        gluLookAt(0.0, 70.0, 0.1,
                  0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0)

    elif camera_mode == 2:
        p1 = players[0]
        rad = math.radians(p1['facing'])

        cam_x = p1['x'] - math.sin(rad) * 9.0
        cam_z = p1['z'] - math.cos(rad) * 9.0
        cam_y = 5.5

        gluLookAt(cam_x, cam_y, cam_z,
                  p1['x'], 1.2, p1['z'],
                  0.0, 1.0, 0.0)

    elif camera_mode == 3:
        target_x, target_z = 0.0, 0.0
        if ball_carrier_id is not None:
            target_x = players[ball_carrier_id]['x']
            target_z = players[ball_carrier_id]['z']
        gluLookAt(0.0, 30.0, 40.0,
                  target_x, 0.0, target_z,
                  0.0, 1.0, 0.0)


def showScreen():
    global window_width, window_height

    window_width = glutGet(GLUT_WINDOW_WIDTH)
    window_height = glutGet(GLUT_WINDOW_HEIGHT)
    if window_height == 0:
        window_height = 1

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    glViewport(0, 0, window_width, window_height)

    setupCamera()
    draw_arena()

    if quicksand['active']: quicksandCircle(quicksand['x'], quicksand['z'], quicksand['radius'])
    for b in speed_boosts:
        if b['active']: speed_boost_cube(b['x'], b['z'], b['angle'])

    if ghost_cloak['active']:
        ghost_cloak_cube(ghost_cloak['x'], ghost_cloak['z'], ghost_cloak['angle'])

    for r in roombas:
        if r['active']:
            boulderRoomba(r['x'], r['z'], r['radius'])

    if game_state in ["COUNTDOWN", "RACING"]:
        draw_ball()
    if goalpost['active']:
        draw_goalpost(goalpost['x'], goalpost['z'])

    run_angle = 0.0
    if game_state in ["RACING", "CHASE"]:
        run_angle = math.sin(frame_count * 0.3) * 45.0

    for p in players:
        p_color = p['color']
        is_carrier = (p['id'] == ball_carrier_id)
        is_human = p['is_human']

        if p['ghost_frames'] > 0:
            p_color = (0.8, 0.8, 0.9)
        elif is_carrier and invincibility_frames > 0:
            if (invincibility_frames // 5) % 2 == 0:
                p_color = (1.0, 1.0, 1.0)

        draw_player(p['x'], p['z'], p_color, limb_angle=run_angle, y_angle=p['facing'], is_carrier=is_carrier,
                    is_human=is_human)

    draw_text(f"ROUND: {current_round} / {max_rounds}", 20, window_height - 30)

    draw_text("SCOREBOARD", window_width - 150, window_height - 30)
    for i in range(5):
        label = "P1 (YOU)" if i == 0 else f"COM {i}"
        draw_text(f"{label}: {scores[i]}", window_width - 150, window_height - 60 - (i * 25))

    if game_state == "COUNTDOWN":
        seconds_left = 3 - (frame_count // 60)
        if seconds_left > 0:
            draw_text(f"GET READY: {seconds_left}", window_width // 2 - 60, window_height // 2)

    elif game_state == "ROUND_OVER":
        draw_text(round_winner_text, window_width // 2 - 120, window_height // 2 + 20)
        draw_text("Resetting...", window_width // 2 - 40, window_height // 2 - 10)

    elif game_state == "MATCH_OVER":
        draw_text("MATCH COMPLETE!", window_width // 2 - 80, window_height // 2 + 30)
        draw_text(round_winner_text, window_width // 2 - 140, window_height // 2)
        draw_text("[PRESS 'R' TO RESTART]", window_width // 2 - 100, window_height // 2 - 30)

    glutSwapBuffers()


def idle():
    global frame_count, game_state, ball_carrier_id, invincibility_frames, current_round, round_winner_text

    for p in players:
        if p['stun_frames'] > 0:
            p['stun_frames'] -= 1
        if p['ghost_frames'] > 0:
            p['ghost_frames'] -= 1

    for b in speed_boosts:
        b['angle'] += 2.0
        if b['angle'] > 360:
            b['angle'] -= 360

    ghost_cloak['angle'] += 3.0
    if ghost_cloak['angle'] > 360:
        ghost_cloak['angle'] -= 360

    if game_state in ["RACING", "CHASE"]:
        for r in roombas:
            if not r['active']:
                continue

            r['x'] += r['dx']
            r['z'] += r['dz']

            dist = math.sqrt(r['x'] ** 2 + r['z'] ** 2)
            if dist > arena_radius - r['radius']:
                nx = r['x'] / dist
                nz = r['z'] / dist

                dot = r['dx'] * nx + r['dz'] * nz

                r['dx'] = r['dx'] - 2 * dot * nx
                r['dz'] = r['dz'] - 2 * dot * nz

                overlap = dist - (arena_radius - r['radius'])
                r['x'] -= nx * overlap
                r['z'] -= nz * overlap

            for p in players:
                if p['ghost_frames'] > 0:
                    continue
                p_dist = math.sqrt((p['x'] - r['x']) ** 2 + (p['z'] - r['z']) ** 2)
                if p_dist < 1.0 + r['radius']:
                    p['stun_frames'] = 90

    if game_state == "COUNTDOWN":
        frame_count += 1
        if frame_count >= 180:
            game_state = "RACING"
            applying_rng_speeds(players)

    elif game_state == "RACING":
        frame_count += 1

        UserControlledPlayer(1.0)

        for p in players:
            if not p['is_human'] and p['stun_frames'] == 0:
                compPlayer_to_target(p, 0.0, 0.0)
            p['x'], p['z'] = enforce_boundaries(p['x'], p['z'], 1.0)

            if ball_collision_check(p['x'], p['z'], 1.0, 1.0):
                ball_carrier_id = p['id']
                p['speed'] = 0.066
                spawn_goalpost(p['x'], p['z'])
                invincibility_frames = 240
                game_state = "CHASE"
                break

    elif game_state == "CHASE":
        frame_count += 1
        if invincibility_frames > 0:
            invincibility_frames -= 1

        if players[0]['ghost_frames'] > 0:
            human_mult = 1.0
        else:
            human_mult = terrain_multiplier(players[0]['x'], players[0]['z'], quicksand['x'], quicksand['z'],
                                            quicksand['radius'])
        UserControlledPlayer(human_mult)

        carrier_x, carrier_z = 0.0, 0.0
        for p in players:
            if p['id'] == ball_carrier_id:
                carrier_x, carrier_z = p['x'], p['z']

                if ghost_cloak['active'] and item_collision_checker(p['x'], p['z'], ghost_cloak['x'], ghost_cloak['z'],
                                                                    ghost_cloak['radius']):
                    ghost_cloak['active'] = False
                    p['ghost_frames'] = 240

                if item_collision_checker(p['x'], p['z'], goalpost['x'], goalpost['z'], goalpost['radius'], 1.0):
                    scores[p['id']] += 1
                    round_winner_text = f"TOUCHDOWN! Player {p['id']} scores!"
                    game_state = "ROUND_OVER"
                    frame_count = 0
                break

        if game_state == "CHASE":
            for p in players:
                if p['id'] != ball_carrier_id:
                    for b in speed_boosts:
                        if b['active'] and item_collision_checker(p['x'], p['z'], b['x'], b['z'], b['radius']):
                            b['active'] = False
                            p['speed'] *= 1.15

                    if invincibility_frames == 0:
                        if item_collision_checker(p['x'], p['z'], carrier_x, carrier_z, 0.6, 0.6):
                            scores[p['id']] += 2
                            tackles[p['id']] += 1
                            round_winner_text = f"TACKLED! Player {p['id']} stole the ball!"
                            game_state = "ROUND_OVER"
                            frame_count = 0
                            break

                if not p['is_human'] and game_state == "CHASE":
                    if p['ghost_frames'] > 0:
                        ai_mult = 1.0
                        eff_qs_rad = 0.0
                    else:
                        ai_mult = terrain_multiplier(p['x'], p['z'], quicksand['x'], quicksand['z'],
                                                     quicksand['radius'])
                        eff_qs_rad = quicksand['radius']

                    target_x, target_z = 0.0, 0.0

                    if p['id'] == ball_carrier_id:
                        evade_x, evade_z = evasion_target_seeker(p['x'], p['z'], goalpost['x'], goalpost['z'], players,
                                                                 p['id'])
                        target_x, target_z = evade_x, evade_z
                    else:
                        closest_b = None
                        min_dist = float('inf')
                        for b in speed_boosts:
                            if b['active']:
                                dist = math.sqrt((p['x'] - b['x']) ** 2 + (p['z'] - b['z']) ** 2)
                                if dist < min_dist:
                                    min_dist = dist
                                    closest_b = b
                        target_x, target_z = (closest_b['x'], closest_b['z']) if closest_b else (carrier_x, carrier_z)

                    smart_x, smart_z = getSmartWaypoint(p['x'], p['z'], target_x, target_z, quicksand['x'],
                                                        quicksand['z'], eff_qs_rad, p['speed'])
                    compPlayer_to_target(p, smart_x, smart_z, ai_mult)

                p['x'], p['z'] = enforce_boundaries(p['x'], p['z'], 1.0)

    elif game_state == "ROUND_OVER":
        frame_count += 1
        if frame_count >= 180:
            if current_round < max_rounds:
                current_round += 1
                reset_round()
            else:
                max_score = max(scores.values())
                top_players = [p_id for p_id, score in scores.items() if score == max_score]

                if len(top_players) == 1:
                    round_winner_text = f"PLAYER {top_players[0]} WINS THE MATCH!"
                else:
                    best_tackles = -1
                    winner_id = None
                    is_draw = False

                    for p_id in top_players:
                        if tackles[p_id] > best_tackles:
                            best_tackles = tackles[p_id]
                            winner_id = p_id
                            is_draw = False
                        elif tackles[p_id] == best_tackles:
                            is_draw = True

                    if is_draw:
                        round_winner_text = "MATCH DRAW! (Tied on Points AND Tackles)"
                    else:
                        round_winner_text = f"PLAYER {winner_id} WINS BY TIEBREAKER!"
                game_state = "MATCH_OVER"

    glutPostRedisplay()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"I am Jose Mourinho")
    init()

    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)

    glutMainLoop()


if __name__ == "__main__":
    main()
