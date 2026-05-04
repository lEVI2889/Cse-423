from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random


# Camera variables
camera_angle = 90.0   # Angle for circular movement in 3rd person
camera_height = 400.0 # Up/Down height
camera_radius = 600.0 # Distance from center
is_first_person = False # Toggle state

fovY = 120  # Field of view
GRID_LENGTH = 600  # Length of grid lines
rand_var = 423
# Player state variables
player_x = 0.0
player_y = 0.0
player_angle = 0.0  # Facing angle in degrees
PLAYER_SPEED = 10.0
ROTATION_SPEED = 5.0

# Enemy variables
NUM_ENEMIES = 5
ENEMY_SPEED = 0.2
enemies = []

# Bullet variables
bullets = []
BULLET_SPEED = 15.0

# Game state variables
player_life = 5
game_score = 0
bullets_missed = 0
game_over = False

# Cheat mode variables
cheat_mode = False
cheat_vision = False
locked_view_angle = 0.0
fire_cooldown = 0

def spawn_enemy():
    """Returns a dictionary containing a new enemy's state."""
    # Spawn randomly within the grid boundaries, keeping a slight buffer from the wall
    return {
        'x': random.uniform(-GRID_LENGTH + 50, GRID_LENGTH - 50),
        'y': random.uniform(-GRID_LENGTH + 50, GRID_LENGTH - 50),
        'scale': random.uniform(0.8, 1.2),  # Start at a random size
        'scale_dir': 0.015 * random.choice([-1, 1])  # Start growing or shrinking randomly
    }

# Initialize the 5 enemies
for _ in range(NUM_ENEMIES):
    enemies.append(spawn_enemy())


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()

    # Set up an orthographic projection that matches window coordinates
    gluOrtho2D(0, 1000, 0, 800)  # left, right, bottom, top

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Draw text at (x, y) in screen coordinates
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    # Restore original projection and modelview matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_shapes():
    glPushMatrix()  # Save the current matrix state
    glColor3f(1, 0, 0)
    glTranslatef(0, 0, 0)
    glutSolidCube(60)  # Take cube size as the parameter
    glTranslatef(0, 0, 100)
    glColor3f(0, 1, 0)
    glutSolidCube(60)

    glColor3f(1, 1, 0)
    glScalef(2, 2, 2)
    gluCylinder(gluNewQuadric(), 40, 5, 150, 10,
                10)  # parameters are: quadric, base radius, top radius, height, slices, stacks
    glTranslatef(100, 0, 100)
    glRotatef(90, 0, 1, 0)  # parameters are: angle, x, y, z
    gluCylinder(gluNewQuadric(), 40, 5, 150, 10, 10)

    glColor3f(0, 1, 1)
    glTranslatef(300, 0, 100)
    gluSphere(gluNewQuadric(), 80, 10, 10)  # parameters are: quadric, radius, slices, stacks

    glPopMatrix()  # Restore the previous matrix state


def keyboardListener(key, x, y):
    global player_x, player_y, player_angle
    global player_life, game_score, bullets_missed, game_over
    global bullets, enemies
    global cheat_mode, cheat_vision, locked_view_angle
    """
    Handles keyboard inputs for player movement, gun rotation, camera updates, and cheat mode toggles.
    """
    if game_over and key != b'r':
        return

    # # Move forward (W key)
    if key == b'w':
        rad = math.radians(player_angle)
        next_x = player_x - math.sin(rad) * PLAYER_SPEED
        next_y = player_y + math.cos(rad) * PLAYER_SPEED
        # Basic collision check with grid boundaries
        if -GRID_LENGTH < next_x < GRID_LENGTH and -GRID_LENGTH < next_y < GRID_LENGTH:
            player_x = next_x
            player_y = next_y

    # # Move backward (S key)
    if key == b's':
        rad = math.radians(player_angle)
        next_x = player_x + math.sin(rad) * PLAYER_SPEED
        next_y = player_y - math.cos(rad) * PLAYER_SPEED
        if -GRID_LENGTH < next_x < GRID_LENGTH and -GRID_LENGTH < next_y < GRID_LENGTH:
            player_x = next_x
            player_y = next_y

    # # Rotate gun left (A key)
    if key == b'a':
        player_angle += ROTATION_SPEED

    # # Rotate gun right (D key)
    if key == b'd':
        player_angle -= ROTATION_SPEED
    # # Toggle cheat mode (C key)
    if key == b'c':
        cheat_mode = not cheat_mode
        if cheat_mode:
            locked_view_angle = player_angle  # Lock camera angle when entering cheat mode

    # # Toggle cheat vision (V key)
    if key == b'v':
        cheat_vision = not cheat_vision

    # # Reset the game if R key is pressed
    if key == b'r':
        # Reset Stats
        player_life = 5
        game_score = 0
        bullets_missed = 0
        game_over = False

        # Reset Player Position
        player_x = 0.0
        player_y = 0.0
        player_angle = 0.0

        # Clear existing entities
        bullets.clear()
        enemies.clear()

        # Respawn new enemies
        for _ in range(NUM_ENEMIES):
            enemies.append(spawn_enemy())

        cheat_mode = False
        cheat_vision = False
        fire_cooldown = 0


def specialKeyListener(key, x, y):
    """
    Handles special key inputs (arrow keys) for adjusting the camera angle and height.
    """
    global camera_angle, camera_height

    #  camera up (UP arrow key)
    if key == GLUT_KEY_UP:
        camera_height += 15.0

    #  camera down (DOWN arrow key)
    if key == GLUT_KEY_DOWN:
        camera_height -= 15.0

    #  camera left (LEFT arrow key) rotates counter-clockwise
    if key == GLUT_KEY_LEFT:
        camera_angle += 5.0

        #  camera right (RIGHT arrow key) rotates clockwise
    if key == GLUT_KEY_RIGHT:
        camera_angle -= 5.0


def mouseListener(button, state, x, y):
    """
    Handles mouse inputs for firing bullets (left click) and toggling camera mode (right click).
    """
    global is_first_person, bullets, player_x, player_y, player_angle, game_over

    # GUARD: Prevent shooting and camera toggling if the game is over
    if game_over:
        return

    # Left mouse button fires a bullet
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        print("Player Bullet Fired!")
        rad = math.radians(player_angle)

        # Calculate velocity components
        velocity_x = -math.sin(rad) * BULLET_SPEED
        velocity_y = math.cos(rad) * BULLET_SPEED

        # Start the bullet slightly in front of the player (near the gun barrel)
        start_x = player_x + (velocity_x * 1.5)
        start_y = player_y + (velocity_y * 1.5)

        bullets.append({
            'x': start_x,
            'y': start_y,
            'dx': velocity_x,
            'dy': velocity_y
        })

    # Right mouse button toggles camera tracking mode
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        is_first_person = not is_first_person

def setupCamera():
    """
    Configures the camera's projection and view settings.
    Uses a perspective projection and positions the camera to look at the target.
    """
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if is_first_person:
        # --- First-Person Mode (True POV) ---
        # Determine which angle the camera should use
        if cheat_mode and not cheat_vision:
            view_rad = math.radians(locked_view_angle)
        else:
            view_rad = math.radians(player_angle)


        cam_x = player_x - math.sin(view_rad) * 5.0
        cam_y = player_y + math.cos(view_rad) * 5.0
        cam_z = 70.0


        look_x = player_x - math.sin(view_rad) * 200
        look_y = player_y + math.cos(view_rad) * 200
        look_z = 45.0
        gluLookAt(cam_x, cam_y, cam_z, look_x, look_y, look_z, 0, 0, 1)

    else:
        # --- Third-Person Orbital Mode ---
        rad = math.radians(camera_angle)
        cam_x = math.cos(rad) * camera_radius
        cam_y = math.sin(rad) * camera_radius

        gluLookAt(cam_x, cam_y, camera_height,
                  0, 0, 0,
                  0, 0, 1)

def idle():
    global enemies, bullets, player_x, player_y
    global player_life, game_score, bullets_missed, game_over
    global cheat_mode, cheat_vision, fire_cooldown, player_angle
    """
    Idle function that runs continuously:
    - Moves enemies and checks player collisions.
    - Moves bullets and checks enemy collisions / out of bounds.
    """


    if game_over:
        glutPostRedisplay()
        return

    if cheat_mode:
        if fire_cooldown > 0:
            fire_cooldown -= 1
        else:

            nearest = None
            nearest_dist = float('inf')
            for e in enemies:
                dx = e['x'] - player_x
                dy = e['y'] - player_y
                dist = math.sqrt(dx ** 2 + dy ** 2)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = e

            if nearest is None:
                pass
            else:


                t_intercept = nearest_dist / BULLET_SPEED


                dx = player_x - nearest['x']
                dy = player_y - nearest['y']
                dist = math.sqrt(dx ** 2 + dy ** 2)
                if dist > 0:
                    enemy_vx = (dx / dist) * ENEMY_SPEED
                    enemy_vy = (dy / dist) * ENEMY_SPEED
                else:
                    enemy_vx, enemy_vy = 0, 0


                future_x = nearest['x'] + enemy_vx * t_intercept
                future_y = nearest['y'] + enemy_vy * t_intercept


                aim_dx = future_x - player_x
                aim_dy = future_y - player_y
                ideal_angle = math.degrees(math.atan2(-aim_dx, aim_dy)) % 360


                current = player_angle % 360
                diff = (ideal_angle - current + 360) % 360
                if diff > 180:
                    diff -= 360

                rotate_step = ROTATION_SPEED
                if abs(diff) <= rotate_step:

                    player_angle = ideal_angle
                else:
                    player_angle += rotate_step if diff > 0 else -rotate_step


                aligned_diff = abs((player_angle % 360) - ideal_angle)
                if aligned_diff > 180:
                    aligned_diff = 360 - aligned_diff

                if aligned_diff < 3.0:
                    rad = math.radians(player_angle)
                    velocity_x = -math.sin(rad) * BULLET_SPEED
                    velocity_y = math.cos(rad) * BULLET_SPEED
                    bullets.append({
                        'x': player_x + velocity_x * 1.5,
                        'y': player_y + velocity_y * 1.5,
                        'dx': velocity_x,
                        'dy': velocity_y
                    })
                    fire_cooldown = 20


    for e in enemies:

        e['scale'] += e['scale_dir']
        if e['scale'] > 1.3 or e['scale'] < 0.7:
            e['scale_dir'] *= -1


        dx = player_x - e['x']
        dy = player_y - e['y']
        distance = math.sqrt(dx ** 2 + dy ** 2)


        if distance < 20:
            player_life -= 1
            print(f"Remaining Player Life: {player_life}")
            e.update(spawn_enemy())
            if player_life <= 0:
                game_over = True
            continue

        if distance > 0:
            e['x'] += (dx / distance) * ENEMY_SPEED
            e['y'] += (dy / distance) * ENEMY_SPEED


    for b in bullets[:]:
        b['x'] += b['dx']
        b['y'] += b['dy']

        hit_enemy = False


        for e in enemies:
            dist = math.sqrt((b['x'] - e['x']) ** 2 + (b['y'] - e['y']) ** 2)
            if dist < 15:
                game_score += 10
                e.update(spawn_enemy())
                bullets.remove(b)
                hit_enemy = True
                break

        if hit_enemy:
            continue


        if abs(b['x']) > GRID_LENGTH or abs(b['y']) > GRID_LENGTH:
            bullets_missed += 1
            print(f"Bullet missed: {bullets_missed}")
            bullets.remove(b)
            if bullets_missed >= 10:
                game_over = True

    glutPostRedisplay()


def draw_player():
    glPushMatrix()


    glTranslatef(player_x, player_y, 0)
    glRotatef(player_angle, 0, 0, 1)


    if game_over:

        glRotatef(-90, 1, 0, 0)

        glTranslatef(0, 0, -20)


    glTranslatef(0, 0, 20)

    glTranslatef(0, 0, 20)


    glPushMatrix()
    glColor3f(0.3, 0.4, 0.1)  # Olive green
    glScalef(1, 0.5, 1.5)
    glutSolidCube(20)
    glPopMatrix()


    glPushMatrix()
    glColor3f(0, 0, 0)
    glTranslatef(0, 0, 20)
    glutSolidSphere(8, 20, 20)
    glPopMatrix()


    glPushMatrix()
    glColor3f(0, 0, 1)
    glTranslatef(-5, 0, -15)
    glRotatef(180, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 3, 2, 15, 10, 10)
    glPopMatrix()


    glPushMatrix()
    glColor3f(0, 0, 1)
    glTranslatef(5, 0, -15)
    glRotatef(180, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 3, 2, 15, 10, 10)
    glPopMatrix()


    glPushMatrix()
    glColor3f(1.0, 0.8, 0.7)
    glTranslatef(-12, 1, 8)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 5, 2, 35, 15, 15)
    glPopMatrix()


    glPushMatrix()
    glColor3f(1.0, 0.8, 0.7)
    glTranslatef(12, 1, 8)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 5, 2, 35, 15, 15)
    glPopMatrix()


    glPushMatrix()
    glColor3f(0.7, 0.7, 0.7)
    glTranslatef(0, 1, 10)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 5, 3, 35, 15, 15)
    glPopMatrix()

    glPopMatrix()  # End of entire player


def draw_enemies():
    for e in enemies:
        glPushMatrix()

        glTranslatef(e['x'], e['y'], 15)


        glScalef(e['scale'], e['scale'], e['scale'])


        glPushMatrix()
        glColor3f(1, 0, 0)  # Red
        glutSolidSphere(12, 20, 20)
        glPopMatrix()


        glPushMatrix()
        glColor3f(0, 0, 0)  # Black
        glTranslatef(0, 8, 8)
        glutSolidSphere(6, 15, 15)
        glPopMatrix()

        glPopMatrix()

def draw_bullets():
    glColor3f(1, 1, 0)
    for b in bullets:
        glPushMatrix()

        glTranslatef(b['x'], b['y'], 20)
        glutSolidCube(4)
        glPopMatrix()

def showScreen():
    """
    Display function to render the game scene:
    - Clears the screen and sets up the camera.
    - Draws everything of the screen
    """

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)

    setupCamera()


    glPointSize(20)
    glBegin(GL_POINTS)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glEnd()


    glBegin(GL_QUADS)
    tile_size = 60


    for x in range(-GRID_LENGTH, GRID_LENGTH, tile_size):
        for y in range(-GRID_LENGTH, GRID_LENGTH, tile_size):

            i = (x + GRID_LENGTH) // tile_size
            j = (y + GRID_LENGTH) // tile_size

            if (i + j) % 2 == 0:
                glColor3f(1, 1, 1)  # White
            else:
                glColor3f(0.7, 0.5, 0.95)  # Light Purple


            glVertex3f(x, y, 0)
            glVertex3f(x + tile_size, y, 0)
            glVertex3f(x + tile_size, y + tile_size, 0)
            glVertex3f(x, y + tile_size, 0)
    glEnd()


    WALL_HEIGHT = 60
    glBegin(GL_QUADS)


    glColor3f(0, 1, 1)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)


    glColor3f(1, 1, 0)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)


    glColor3f(0, 0, 1)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)


    glColor3f(0, 1, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)
    glEnd()


    if game_over:

        draw_text(350, 600, f"Game is Over. Your Score is {game_score}.")
        draw_text(350, 570, "Press 'R' to RESTART the Game.")
    else:

        draw_text(10, 770, f"Player Life Remaining: {player_life}")
        draw_text(10, 740, f"Game Score: {game_score}")
        draw_text(10, 710, f"Player Bullet Missed: {bullets_missed}")

    draw_player()
    draw_enemies()
    draw_bullets()

    # Swap buffers for smooth rendering (double buffering)
    glutSwapBuffers()


# Main function to set up OpenGL window and loop
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)  # Double buffering, RGB color, depth test
    glutInitWindowSize(1000, 800)  # Window size
    glutInitWindowPosition(0, 0)  # Window position
    wind = glutCreateWindow(b"3D OpenGL Intro")  # Create the window

    glutDisplayFunc(showScreen)  # Register display function
    glutKeyboardFunc(keyboardListener)  # Register keyboard listener
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)  # Register the idle function to move the bullet automatically

    glutMainLoop()  # Enter the GLUT main loop


if __name__ == "__main__":
    main()
