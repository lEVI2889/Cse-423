from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, random, time

WIN_W, WIN_H = 1280, 900
last_time = 0
game_state = "START"
score = 0
lifespan = 3          # Player starts with 3 lives
cam_mode = 1
orbit_angle, orbit_height, orbit_distance = 45.0, 200.0, 600.0
spawn_timer = 0
death_reason = ""

class Object3D:
    def __init__(self, pos, t, color):
        self.pos = pos; self.type = t; self.color = color
        self.size = random.uniform(20, 30)   # Same size for both food and obstacles

def dist(a, b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def get_segs(history, n, sd):
    """Sample n evenly-spaced positions along the snake history trail."""
    res = []
    if len(history) < 2: return res
    res.append(history[0])
    for i in range(1, n):
        target_d = i * sd
        cd = 0.0
        found = False
        # Walk from the beginning each time to get the correct interpolated point
        for idx in range(len(history)-1):
            d = dist(history[idx], history[idx+1])
            if cd + d >= target_d:
                t = (target_d - cd) / d if d > 0 else 0
                p = [history[idx][j]+(history[idx+1][j]-history[idx][j])*t for j in range(3)]
                res.append(p); found = True; break
            cd += d
        if not found: res.append(history[-1])
    return res

class Snake:
    def __init__(self, is_player, pos, yaw=0.0):
        self.is_player = is_player
        self.pos = list(pos)
        self.yaw = yaw; self.pitch = 0.0
        self.speed = 150.0
        # Pre-stretch tail to prevent instant self-collision
        self.history = [[pos[0]-i*6*math.cos(yaw), pos[1]-i*6*math.sin(yaw), pos[2]] for i in range(200)]
        self.segments = 10; self.seg_dist = 20.0
        self.autopilot = False
        self.head_r = 12.0; self.body_r = 10.0
        self.color = (0.2, 1.0, 0.4) if is_player else (1.0, 0.25, 0.25)

    def forward(self):
        cp = math.cos(self.pitch)
        return [math.cos(self.yaw)*cp, math.sin(self.yaw)*cp, math.sin(self.pitch)]

    def update(self, dt):
        if not self.is_player or self.autopilot:
            self.steer(dt)
        self.pitch = max(-1.4, min(1.4, self.pitch))
        fw = self.forward()
        for i in range(3): self.pos[i] += fw[i]*self.speed*dt
        self.history.insert(0, list(self.pos))
        if len(self.history) > 2000: self.history.pop()

    def steer(self, dt):
        target = None; best = 9999
        for o in objects:
            if o.type == 'food':
                d = dist(self.pos, o.pos)
                if d < best: best=d; target=o.pos
        if target is None and not self.is_player and player:
            target = player.pos
        if target:
            dx,dy,dz = target[0]-self.pos[0], target[1]-self.pos[1], target[2]-self.pos[2]
            dy_ = (math.atan2(dy,dx) - self.yaw)
            while dy_ >  math.pi: dy_ -= 2*math.pi
            while dy_ < -math.pi: dy_ += 2*math.pi
            self.yaw += dy_*2.5*dt
            dp = math.atan2(dz, math.sqrt(dx*dx+dy*dy)) - self.pitch
            self.pitch += dp*2.5*dt

player, rivals, objects = None, [], []

# 5 distinct colors for the AI rivals
RIVAL_COLORS = [
    (1.0, 0.2, 0.2),   # Red
    (1.0, 0.5, 0.0),   # Orange
    (0.8, 0.2, 1.0),   # Purple
    (0.2, 0.8, 1.0),   # Cyan
    (1.0, 0.2, 0.7),   # Pink
    (1.0, 1.0, 0.2),   # Yellow
]

def spawn_obj(t):
    base = player.pos if player else [0,0,0]
    r  = random.uniform(400, 1500)
    th = random.uniform(0, 2*math.pi)
    ph = random.uniform(-math.pi/2, math.pi/2)
    p = [base[0]+r*math.cos(th)*math.cos(ph),
         base[1]+r*math.sin(th)*math.cos(ph),
         base[2]+r*math.sin(ph)]
    color = (1,.2,.2) if t=='obstacle' else (1,.85,.1)
    objects.append(Object3D(p, t, color))

def init_game():
    global player, rivals, objects, score, game_state, spawn_timer, death_reason, lifespan
    death_reason = ""
    lifespan = 3          # Reset to 3 lives every new game
    player = Snake(True, [0,0,0], 0.0)
    # Spawn 6 AI rivals at different angles around the player
    rivals = []
    spawn_radius = 600
    for i in range(6):
        angle = (i / 6) * 2 * math.pi
        sx = spawn_radius * math.cos(angle)
        sy = spawn_radius * math.sin(angle)
        yaw = angle + math.pi          # Face toward player initially
        color = RIVAL_COLORS[i % len(RIVAL_COLORS)]
        s = Snake(False, [sx, sy, 0], yaw)
        s.color = color
        rivals.append(s)
    objects = []; score = 0; spawn_timer = 0
    for _ in range(120): spawn_obj('food')
    for _ in range(150): spawn_obj('obstacle')
    game_state = "PLAY"

def begin_hud():
    """Enter 2D HUD mode: pixel coords, clean ortho."""
    glViewport(0, 0, WIN_W, WIN_H)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

def end_hud():
    """Exit 2D HUD mode: restore projection."""
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def hud_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text at pixel coordinates. Must be called between begin_hud/end_hud."""
    glRasterPos2f(float(x), float(y))
    for c in text: glutBitmapCharacter(font, ord(c))

def draw_shaded_cube(s, r, g, b):
    h = s / 2.0
    glBegin(GL_QUADS)
    glColor3f(r, g, b)
    glVertex3f(-h, -h,  h); glVertex3f( h, -h,  h)
    glVertex3f( h,  h,  h); glVertex3f(-h,  h,  h)
    glColor3f(r*0.5, g*0.5, b*0.5)
    glVertex3f(-h, -h, -h); glVertex3f(-h,  h, -h)
    glVertex3f( h,  h, -h); glVertex3f( h, -h, -h)
    glColor3f(r*0.9, g*0.9, b*0.9)
    glVertex3f(-h,  h, -h); glVertex3f(-h,  h,  h)
    glVertex3f( h,  h,  h); glVertex3f( h,  h, -h)
    glColor3f(r*0.6, g*0.6, b*0.6)
    glVertex3f(-h, -h, -h); glVertex3f( h, -h, -h)
    glVertex3f( h, -h,  h); glVertex3f(-h, -h,  h)
    glColor3f(r*0.8, g*0.8, b*0.8)
    glVertex3f( h, -h, -h); glVertex3f( h,  h, -h)
    glVertex3f( h,  h,  h); glVertex3f( h, -h,  h)
    glColor3f(r*0.7, g*0.7, b*0.7)
    glVertex3f(-h, -h, -h); glVertex3f(-h, -h,  h)
    glVertex3f(-h,  h,  h); glVertex3f(-h,  h, -h)
    glEnd()

def draw_cylinder(p1, p2, r1, r2, color):
    # Now draws a box-shaped segment instead of a cylinder
    dx,dy,dz = p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]
    d = math.sqrt(dx*dx+dy*dy+dz*dz)
    if d < 0.1: return
    glPushMatrix(); glColor3f(*color)
    glTranslatef(*p1)
    # Rotation to align with direction vector
    ax, ay = -dy, dx
    mag = math.sqrt(ax*ax+ay*ay)
    if mag > 0.001:
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dz/d))))
        glRotatef(angle, ax, ay, 0)
    elif dz < 0:
        glRotatef(180, 1, 0, 0)
    
    # Draw a stretched cube
    glTranslatef(0, 0, d/2.0)
    avg_r = (r1 + r2) / 2.0
    glScalef(0.8, 0.8, d * 0.8 / (avg_r * 2.0))
    draw_shaded_cube(avg_r * 2.0, color[0], color[1], color[2])
    
    glPopMatrix()

def draw_grid():
    glColor3f(0.05, 0.1, 0.2)  # Much fainter blue to reduce eye strain
    glBegin(GL_QUADS)
    s = 250; R = 900
    px = int(player.pos[0]//s)*s
    py = int(player.pos[1]//s)*s
    pz = int(player.pos[2]//s)*s
    n = int(R/s)+1
    thick = 2.0
    for i in range(-n, n+1):
        for j in range(-n, n+1):
            for k in range(-n, n+1):
                x,y,z = px+i*s, py+j*s, pz+k*s
                if dist([x,y,z], player.pos) > R: continue
                if dist([x+s,y,z], player.pos) <= R:
                    glVertex3f(x, y-thick, z-thick)
                    glVertex3f(x+s, y-thick, z-thick)
                    glVertex3f(x+s, y+thick, z+thick)
                    glVertex3f(x, y+thick, z+thick)
                if dist([x,y+s,z], player.pos) <= R:
                    glVertex3f(x-thick, y, z-thick)
                    glVertex3f(x+thick, y, z-thick)
                    glVertex3f(x+thick, y+s, z+thick)
                    glVertex3f(x-thick, y+s, z+thick)
                if dist([x,y,z+s], player.pos) <= R:
                    glVertex3f(x-thick, y-thick, z)
                    glVertex3f(x+thick, y-thick, z)
                    glVertex3f(x+thick, y+thick, z+s)
                    glVertex3f(x-thick, y+thick, z+s)
    glEnd()

def draw_circular_minimap():
    """Draw radar in top-right corner using authorized functions."""
    MAP_SIZE = 220
    MAP_X = WIN_W - MAP_SIZE - 10
    MAP_Y = WIN_H - MAP_SIZE - 10
    RADAR_R = 1500.0

    glViewport(MAP_X, MAP_Y, MAP_SIZE, MAP_SIZE)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(-RADAR_R, RADAR_R, -RADAR_R, RADAR_R)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    
    # Background (Dark square)
    glColor3f(0.0, 0.0, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(-RADAR_R, -RADAR_R)
    glVertex2f(RADAR_R, -RADAR_R)
    glVertex2f(RADAR_R, RADAR_R)
    glVertex2f(-RADAR_R, RADAR_R)
    glEnd()

    # Center crosshair using very thin quads
    glColor3f(0.1, 0.4, 0.6)
    glBegin(GL_QUADS)
    glVertex2f(-RADAR_R, -10); glVertex2f(RADAR_R, -10)
    glVertex2f(RADAR_R, 10);   glVertex2f(-RADAR_R, 10)
    glVertex2f(-10, -RADAR_R); glVertex2f(10, -RADAR_R)
    glVertex2f(10, RADAR_R);   glVertex2f(-10, RADAR_R)
    glEnd()

    # Draw blips relative to player
    glTranslatef(-player.pos[0], -player.pos[1], 0)
    glPointSize(6)
    glBegin(GL_POINTS)
    for o in objects:
        rx = o.pos[0]-player.pos[0]; ry = o.pos[1]-player.pos[1]
        if math.sqrt(rx*rx+ry*ry) > 1450: continue
        if o.type=='food': glColor3f(1,1,0)
        else:              glColor3f(0.5,0.5,0.6)
        glVertex2f(o.pos[0], o.pos[1])
    # Draw all rival dots — only if within radar radius
    for rv in rivals:
        rrx = rv.pos[0]-player.pos[0]; rry = rv.pos[1]-player.pos[1]
        if math.sqrt(rrx*rrx+rry*rry) > 1450: continue
        glColor3f(*rv.color)
        glVertex2f(rv.pos[0], rv.pos[1])
    glEnd()
    
    glPointSize(10)
    glBegin(GL_POINTS)
    glColor3f(0.2, 1.0, 0.4); glVertex2f(player.pos[0], player.pos[1])
    glEnd()
    glPointSize(1)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    # CRITICAL: restore full-window viewport after minimap
    glViewport(0, 0, WIN_W, WIN_H)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    if game_state not in ("PLAY","OVER"):
        # Start screen
        begin_hud()
        glColor3f(0.2, 1.0, 0.5)
        hud_text(WIN_W//2-120, WIN_H//2+30, "3D GRID SNAKE", GLUT_BITMAP_TIMES_ROMAN_24)
        glColor3f(1,1,1)
        hud_text(WIN_W//2-110, WIN_H//2-10, "PRESS ENTER TO START")
        hud_text(WIN_W//2-140, WIN_H//2-40, "WASD=Steer  Arrows=Axis  C=Cheat  1/2/3=Cam")
        end_hud()
        glutSwapBuffers(); return

    # 3D Viewport
    glViewport(0, 0, WIN_W, WIN_H)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(65, WIN_W/WIN_H, 1, 12000)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()

    if cam_mode == 1:
        # Orbit camera — 3rd person rotating around the snake
        r = math.radians(orbit_angle)
        cx = player.pos[0] + orbit_distance*math.cos(r)
        cy = player.pos[1] + orbit_distance*math.sin(r)
        cz = player.pos[2] + orbit_height
        gluLookAt(cx, cy, cz, player.pos[0], player.pos[1], player.pos[2], 0, 0, 1)
    elif cam_mode == 2:
        # First-person snake-eye pushed slightly ahead and above the head to prevent clipping
        fw = player.forward()
        offset = player.head_r * 2.5
        eye_x = player.pos[0] + fw[0]*offset
        eye_y = player.pos[1] + fw[1]*offset
        eye_z = player.pos[2] + fw[2]*offset + 5.0
        gluLookAt(eye_x, eye_y, eye_z,
                  eye_x+fw[0], eye_y+fw[1], eye_z+fw[2],
                  0, 0, 1)
    else:
        # TOP-DOWN view — camera locked directly above the snake, looking down
        # Camera sits 1200 units above the player, looks straight down (-Z)
        # Forward direction of snake used to keep north orientation stable
        top_h = 1200.0
        # Use snake's yaw to keep north "up" on screen (snake always faces upward on screen)
        north_x = math.cos(player.yaw)
        north_y = math.sin(player.yaw)
        gluLookAt(
            player.pos[0], player.pos[1], player.pos[2] + top_h,  # eye above player
            player.pos[0], player.pos[1], player.pos[2],           # look at player
            north_x, north_y, 0                                    # "up" = snake forward direction
        )

    draw_grid()

    # Draw targeting lines to closest objects for depth perception
    closest_food = None; min_f = 1200
    closest_obs = None;  min_o = 1200
    for o in objects:
        d = dist(player.pos, o.pos)
        if o.type == 'food' and d < min_f:
            min_f = d; closest_food = o
        elif o.type == 'obstacle' and d < min_o:
            min_o = d; closest_obs = o
            
    glBegin(GL_QUADS)
    if closest_food:
        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(player.pos[0]-2, player.pos[1]-2, player.pos[2])
        glVertex3f(player.pos[0]+2, player.pos[1]+2, player.pos[2])
        glVertex3f(closest_food.pos[0]+2, closest_food.pos[1]+2, closest_food.pos[2])
        glVertex3f(closest_food.pos[0]-2, closest_food.pos[1]-2, closest_food.pos[2])
    if closest_obs:
        glColor3f(1.0, 0.2, 0.2)
        glVertex3f(player.pos[0]-2, player.pos[1]-2, player.pos[2])
        glVertex3f(player.pos[0]+2, player.pos[1]+2, player.pos[2])
        glVertex3f(closest_obs.pos[0]+2, closest_obs.pos[1]+2, closest_obs.pos[2])
        glVertex3f(closest_obs.pos[0]-2, closest_obs.pos[1]-2, closest_obs.pos[2])
    glEnd()

    # Draw objects
    t = time.time()
    for o in objects:
        glPushMatrix(); glTranslatef(*o.pos)
        s = o.size*(1.0+0.28*math.sin(t*3+o.pos[0]))
        if o.type == 'food':
            # Food = two crossed cubes spinning (star shape), soft warm yellow
            glPushMatrix()
            glRotatef(t * 80 + o.pos[0], 1, 1, 0)
            draw_shaded_cube(s, 0.85, 0.78, 0.2)   # Soft warm yellow (not glaring)
            glPopMatrix()
            glPushMatrix()
            glRotatef(t * 80 + o.pos[0] + 45, 0, 1, 1)
            draw_shaded_cube(s * 0.7, 0.78, 0.68, 0.18)   # Slightly darker gold
            glPopMatrix()
        else:
            # Obstacle = slow spinning cube, muted brick red
            glRotatef(t * 30 + o.pos[0], 1, 0, 1)
            draw_shaded_cube(s, 0.72, 0.2, 0.2)   # Muted dark red
        glPopMatrix()

    # Draw all snakes (player + all rivals)
    for snake in [player] + rivals:
        segs = get_segs(snake.history, snake.segments, snake.seg_dist)
        for i in range(len(segs)-1):
            f = 1.0 - i/max(len(segs),1)
            c = (snake.color[0]*f, snake.color[1]*f, snake.color[2]*f)
            draw_cylinder(segs[i], segs[i+1], snake.body_r*f, snake.body_r*f*0.8, c)
        glPushMatrix(); glTranslatef(*snake.pos)
        
        # Orient the head box to face forward
        fw = snake.forward()
        ax, ay = -fw[1], fw[0]
        mag = math.sqrt(ax*ax+ay*ay)
        if mag > 0.001:
            angle = math.degrees(math.acos(max(-1.0, min(1.0, fw[2]))))
            glRotatef(angle, ax, ay, 0)
        elif fw[2] < 0:
            glRotatef(180, 1, 0, 0)
            
        if snake.is_player:
            draw_shaded_cube(snake.head_r * 2.0, 1.0, 1.0, 1.0)
        else:
            draw_shaded_cube(snake.head_r * 2.0, snake.color[0], snake.color[1], snake.color[2])
        glPopMatrix()

    # Circular minimap
    draw_circular_minimap()

    # === HUD OVERLAY ===
    begin_hud()

    # --- LEFT SIDE: Player Score & Status ---
    glColor3f(1.0, 1.0, 0.0)   # Yellow
    hud_text(15, WIN_H - 26, f"SCORE: {score}", GLUT_BITMAP_TIMES_ROMAN_24)

    glColor3f(0.8, 0.9, 1.0)
    hud_text(15, WIN_H - 55, f"SNAKE SIZE: {player.segments}")

    # Lifespan display as text boxes
    hearts = "[+] " * lifespan + "[ ] " * (3 - lifespan)
    if lifespan == 3:   glColor3f(0.2, 1.0, 0.4)   # Green - full health
    elif lifespan == 2: glColor3f(1.0, 1.0, 0.0)   # Yellow - warning
    else:               glColor3f(1.0, 0.2, 0.2)   # Red - critical
    hud_text(15, WIN_H - 78, f"LIVES: {hearts}")

    glColor3f(0.7, 0.85, 1.0)
    cam_names = {1: 'ORBIT [1]', 2: 'SNAKE-EYE [2]', 3: 'TOP-DOWN [3]'}
    hud_text(15, WIN_H - 101, f"CAM: {cam_names.get(cam_mode, '?')}")

    if player.autopilot:
        glColor3f(0.2, 1.0, 0.4)
        hud_text(15, WIN_H - 124, "CHEAT: ON [C]")
    else:
        glColor3f(1.0, 0.4, 0.4)
        hud_text(15, WIN_H - 124, "CHEAT: OFF [C]")

    # Controls at bottom-left
    glColor3f(0.45, 0.45, 0.45)
    hud_text(15, 10, "WASD=Steer  Arrows=Camera/Snap  R=Restart")

    if game_state == "OVER":
        glColor3f(1.0, 0.1, 0.1)
        hud_text(WIN_W//2 - 135, WIN_H//2 + 20,
                 f"GAME OVER!  SCORE: {score}", GLUT_BITMAP_TIMES_ROMAN_24)
        if death_reason:
            glColor3f(1.0, 0.5, 0.0)
            hud_text(WIN_W//2 - 120, WIN_H//2 - 20, death_reason, GLUT_BITMAP_HELVETICA_18)
        glColor3f(1.0, 1.0, 1.0)
        hud_text(WIN_W//2 - 85, WIN_H//2 - 45, "Press  R  to Restart")

    if game_state == "PAUSE":
        glColor3f(1.0, 0.85, 0.0)
        hud_text(WIN_W//2 - 80, WIN_H//2 + 20,
                 "PAUSED", GLUT_BITMAP_TIMES_ROMAN_24)
        glColor3f(1.0, 1.0, 1.0)
        hud_text(WIN_W//2 - 120, WIN_H//2 - 18, "Press SPACE to Resume")

    end_hud()
    glutSwapBuffers()

def update():
    global last_time, game_state, score, spawn_timer, death_reason, lifespan
    now = time.time()
    dt = min(now - last_time, 0.05) if last_time > 0 else 0.016
    last_time = now

    if game_state == "PAUSE":
        glutPostRedisplay(); return

    if game_state == "PLAY":
        player.update(dt)
        for rv in rivals: rv.update(dt)
        spawn_timer += dt

        if spawn_timer > 2.0:
            p_segs = get_segs(player.history, player.segments, player.seg_dist)

            if not player.autopilot:
                # Touch any AI head = GAME OVER
                for rv in rivals:
                    if dist(player.pos, rv.pos) < player.head_r + rv.head_r:
                        game_state = "OVER"; death_reason = "Killed by AI Snake Head!"
                # Touch own tail = GAME OVER
                for i, p in enumerate(p_segs):
                    if i > 15 and dist(player.pos, p) < player.head_r + player.body_r*0.3:
                        game_state = "OVER"; death_reason = "You bit your own tail!"
                # Touch any AI body = GAME OVER
                for rv in rivals:
                    r_segs = get_segs(rv.history, rv.segments, rv.seg_dist)
                    for p in r_segs:
                        if dist(player.pos, p) < player.head_r + rv.body_r*0.3:
                            game_state = "OVER"; death_reason = "Crashed into AI Snake Body!"
                # Touch obstacle = LOSE 1 LIFE (not instant GAME OVER)
                for o in objects[:]:
                    if o.type == 'obstacle' and dist(player.pos, o.pos) < player.head_r + o.size*0.5:
                        lifespan -= 1
                        objects.remove(o)   # Destroy the obstacle that hit you
                        spawn_obj('obstacle')  # Respawn a new one far away
                        if lifespan <= 0:
                            game_state = "OVER"; death_reason = "Ran out of Lives! (Hit 3 Red Obstacles)"
                        break

            # Player eats food (always active) - with vacuum effect to make it easy
            for o in objects[:]:
                if o.type == 'food':
                    d = dist(player.pos, o.pos)
                    if d < player.head_r + o.size * 8.0:
                        # Vacuum pull towards player
                        o.pos[0] += (player.pos[0] - o.pos[0]) * 0.15
                        o.pos[1] += (player.pos[1] - o.pos[1]) * 0.15
                        o.pos[2] += (player.pos[2] - o.pos[2]) * 0.15
                    
                    if d < player.head_r + o.size * 1.5:
                        score += 10
                        player.segments += 1
                        objects.remove(o); spawn_obj('food')

            # Each rival eats food and respawns if it hits player tail
            for rv in rivals:
                for o in objects[:]:
                    if o.type == 'food' and dist(rv.pos, o.pos) < rv.head_r + o.size*0.6:
                        rv.segments += 1
                        objects.remove(o); spawn_obj('food')
                        break
                # Rival crashes into player tail -> respawn it away
                for p in p_segs:
                    if dist(rv.pos, p) < rv.head_r + player.body_r*0.75:
                        angle = random.uniform(0, 2*math.pi)
                        rx = player.pos[0] + 1800*math.cos(angle)
                        ry = player.pos[1] + 1800*math.sin(angle)
                        rv.pos = [rx, ry, 0]
                        rv.history = [[rx - i*6*math.cos(rv.yaw), ry - i*6*math.sin(rv.yaw), 0] for i in range(200)]
                        rv.segments = 10
                        break

        # Procedural infinite world
        for o in objects[:]:
            if dist(player.pos, o.pos) > 2600:
                objects.remove(o)
                spawn_obj('food' if random.random() < 0.4 else 'obstacle')

    glutPostRedisplay()

def kb(key, x, y):
    global game_state, cam_mode
    k = key.lower()
    if k == b'\r' and game_state == "START": init_game()
    if k == b'r'  and game_state == "OVER":  init_game()
    if k == b' ':  # Spacebar = pause/resume
        if   game_state == "PLAY":  game_state = "PAUSE"
        elif game_state == "PAUSE": game_state = "PLAY"
    if k == b'1': cam_mode = 1
    if k == b'2': cam_mode = 2
    if k == b'3': cam_mode = 3
    if k == b'c' and player: player.autopilot = not player.autopilot

    if player and not player.autopilot:
        if k == b'a': player.yaw += 0.3
        if k == b'd': player.yaw -= 0.3
        if k == b'w': player.pitch = min(1.4, player.pitch + 0.3)
        if k == b's': player.pitch = max(-1.4, player.pitch - 0.3)

def sp(key, x, y):
    global orbit_angle, orbit_height, orbit_distance
    if player and not player.autopilot:
        if key == GLUT_KEY_UP:    player.yaw, player.pitch = math.pi/2, 0
        if key == GLUT_KEY_DOWN:  player.yaw, player.pitch = -math.pi/2, 0
        if key == GLUT_KEY_LEFT:  player.yaw, player.pitch = math.pi, 0
        if key == GLUT_KEY_RIGHT: player.yaw, player.pitch = 0.0, 0

def mouse(btn, state, x, y):
    # Left click to zoom in, right click to zoom out orbit camera
    global orbit_distance
    if btn == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        orbit_distance = max(100.0, orbit_distance - 50.0)
    if btn == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        orbit_distance = min(2000.0, orbit_distance + 50.0)

glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
glutInitWindowSize(WIN_W, WIN_H)
glutCreateWindow(b"3D Grid Snake - Volumetric Simulation")
glutDisplayFunc(display)
glutIdleFunc(update)
glutKeyboardFunc(kb)
glutSpecialFunc(sp)
glutMouseFunc(mouse)
glutMainLoop()