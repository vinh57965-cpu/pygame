import math
import random
import sys
import pygame # type: ignore

# Khởi tạo Pygame
pygame.init()
pygame.font.init()

# Cấu hình kích thước cửa sổ
WIDTH, HEIGHT = 720, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Game Bắn Trứng - Python Edition")
clock = pygame.time.Clock()
FPS = 60

# Font chữ giao diện
FONT_SM = pygame.font.SysFont("Arial", 16)
FONT_MD = pygame.font.SysFont("Arial", 20, bold=True)
FONT_LG = pygame.font.SysFont("Arial", 36, bold=True)

# Thông số quả trứng và lưới tổ ong (Hexagonal Grid)
R = 27
DX = R * 2
DY = int(R * 1.72)
ROWS = 20
COLS = 13
SHOOTER = {"x": WIDTH // 2, "y": 830}

# Danh sách màu sắc của các quả trứng
COLORS = [
    (239, 68, 68),    # Đỏ
    (59, 130, 246),   # Xanh dương
    (34, 197, 94),    # Xanh lá
    (250, 204, 21),   # Vàng
    (168, 85, 247),   # Tím
]

# Trạng thái trò chơi
grid = []
score = 0
level = 1
shots = 0
current_color = None
next_color = None
projectile = None
game_over = False
won = False
paused = False


def get_position(r, c):
    """Tính tọa độ pixel (x, y) chuẩn xác cho lưới lục giác"""
    x = R + c * DX + (r % 2) * R
    y = R + r * DY
    return x, y


def is_valid(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS


def get_neighbors(r, c):
    """Lấy danh sách các ô lân cận chuẩn xác theo quy tắc lưới lục giác"""
    s = -1 if r % 2 == 0 else 0
    n_list = [
        (r, c - 1),
        (r, c + 1),
        (r - 1, c + s),
        (r - 1, c + s + 1),
        (r + 1, c + s),
        (r + 1, c + s + 1),
    ]
    return [(nr, nc) for nr, nc in n_list if is_valid(nr, nc)]


def reset_game():
    global grid, score, level, shots, current_color, next_color, projectile, game_over, won, paused
    grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
    score = 0
    level = 1
    shots = 0
    game_over = False
    won = False
    paused = False
    projectile = None

    # Khởi tạo 6 hàng trứng ban đầu
    for r in range(6):
        for c in range(COLS):
            grid[r][c] = random.choice(COLORS)

    current_color = random.choice(COLORS)
    next_color = random.choice(COLORS)


def draw_bubble(surface, x, y, color, radius=R):
    """Vẽ quả trứng với hiệu ứng 3D nổi bật và viền sáng"""
    pygame.draw.circle(surface, color, (int(x), int(y)), radius)
    pygame.draw.circle(surface, (255, 255, 255), (int(x), int(y)), radius, 2)
    
    # Điểm phản chiếu ánh sáng (Highlight)
    highlight_x = int(x - radius * 0.35)
    highlight_y = int(y - radius * 0.4)
    pygame.draw.circle(
        surface, (255, 255, 255, 200), (highlight_x, highlight_y), max(2, int(radius * 0.2))
    )


def find_cluster(sr, sc):
    """Thuật toán tìm cụm trứng cùng màu liên thông"""
    color = grid[sr][sc]
    stack = [(sr, sc)]
    seen = {(sr, sc)}
    found = []
    while stack:
        r, c = stack.pop()
        found.append((r, c))
        for nr, nc in get_neighbors(r, c):
            if (nr, nc) not in seen and grid[nr][nc] == color:
                seen.add((nr, nc))
                stack.append((nr, nc))
    return found


def remove_floating():
    """Thuật toán quét và làm rơi các chùm trứng bị mất liên kết với hàng trên cùng"""
    connected = set()
    stack = []
    for c in range(COLS):
        if grid[0][c]:
            stack.append((0, c))

    while stack:
        r, c = stack.pop()
        if (r, c) in connected:
            continue
        connected.add((r, c))
        for nr, nc in get_neighbors(r, c):
            if grid[nr][nc] and (nr, nc) not in connected:
                stack.append((nr, nc))

    removed = 0
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] and (r, c) not in connected:
                grid[r][c] = None
                removed += 1
    global score
    score += removed * 15


def choose_cell():
    """Chọn ô trống tối ưu nhất dựa trên khoảng cách thực tế để tránh lệch vị trí"""
    best_cell = None
    min_dist = float('inf')

    for r in range(ROWS):
        for c in range(COLS):
            if not grid[r][c]:
                px, py = get_position(r, c)
                touches_top = (r == 0)
                touches_bubble = any(grid[nr][nc] is not None for nr, nc in get_neighbors(r, c))

                if touches_top or touches_bubble:
                    dist = math.hypot(px - projectile["x"], py - projectile["y"])
                    if dist < min_dist:
                        min_dist = dist
                        best_cell = (r, c)
    return best_cell


def attach_projectile():
    global projectile, current_color, next_color, shots, game_over, won, score
    cell = choose_cell()
    if cell:
        r, c = cell
        grid[r][c] = projectile["color"]
        group = find_cluster(r, c)
        if len(group) >= 3:
            for ar, ac in group:
                grid[ar][ac] = None
            score += len(group) * 20
            remove_floating()

    projectile = None
    shots += 1
    current_color = next_color
    next_color = random.choice(COLORS)

    # Kiểm tra điều kiện chiến thắng
    if all(all(cell is None for cell in row) for row in grid):
        won = True

    # Kiểm tra điều kiện thua (trứng chạm vạch cảnh báo)
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] and get_position(r, c)[1] >= 755:
                game_over = True

    if shots % 8 == 0 and not won and not game_over:
        drop_new_row()


def drop_new_row():
    global game_over
    for r in range(ROWS - 1, 0, -1):
        grid[r] = list(grid[r - 1])
    grid[0] = [random.choice(COLORS) for _ in range(COLS)]

    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] and get_position(r, c)[1] >= 755:
                game_over = True


def update_projectile():
    if not projectile:
        return
    projectile["x"] += projectile["vx"]
    projectile["y"] += projectile["vy"]

    # Phản xạ khi chạm tường trái / phải
    if projectile["x"] < R:
        projectile["x"] = R
        projectile["vx"] = abs(projectile["vx"])
    elif projectile["x"] > WIDTH - R:
        projectile["x"] = WIDTH - R
        projectile["vx"] = -abs(projectile["vx"])

    # Va chạm trần nhà hoặc các quả trứng khác trên lưới
    hit = projectile["y"] < R
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c]:
                px, py = get_position(r, c)
                if math.hypot(px - projectile["x"], py - projectile["y"]) < R * 2 - 3:
                    hit = True
                    break
        if hit:
            break

    if hit:
        attach_projectile()


def draw_game():
    screen.fill((15, 23, 42))

    # Khu vực nền game chính
    pygame.draw.rect(screen, (30, 58, 138), (0, 0, WIDTH, HEIGHT), border_radius=15)

    # Vạch đỏ cảnh báo nguy hiểm
    pygame.draw.line(screen, (239, 68, 68), (0, 755), (WIDTH, 755), 2)

    # Vẽ toàn bộ trứng đang nằm trên lưới
    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c]:
                px, py = get_position(r, c)
                draw_bubble(screen, px, py, grid[r][c])

    # Vẽ đường ngắm khi di chuyển chuột
    mx, my = pygame.mouse.get_pos()
    dx, dy = mx - SHOOTER["x"], my - SHOOTER["y"]
    if dy < -20 and not projectile and not game_over and not won and not paused:
        length = math.hypot(dx, dy) or 1
        vx, vy = dx / length, dy / length
        curr_x, curr_y = SHOOTER["x"], SHOOTER["y"]
        pygame.draw.line(screen, (255, 255, 255), (curr_x, curr_y), (curr_x + vx * 350, curr_y + vy * 350), 2)

    # Vẽ bệ súng và quả trứng tiếp theo
    draw_bubble(screen, SHOOTER["x"], SHOOTER["y"], current_color, R + 2)
    
    score_text = FONT_MD.render(f"Điểm: {score}", True, (255, 255, 255))
    level_text = FONT_MD.render(f"Màn: {level}", True, (255, 255, 255))
    next_label = FONT_MD.render("TIẾP THEO", True, (148, 163, 184))

    screen.blit(score_text, (WIDTH - 180, 20))
    screen.blit(level_text, (WIDTH - 80, 20))

    screen.blit(next_label, (WIDTH - 120, 795))
    draw_bubble(screen, WIDTH - 80, 835, next_color, 18)

    if projectile:
        draw_bubble(screen, projectile["x"], projectile["y"], projectile["color"])

    # Bảng thông báo trạng thái (Tạm dừng, Thắng, Thua)
    if game_over or won or paused:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 220))
        screen.blit(overlay, (0, 0))

        msg = "TẠM DỪNG" if paused else ("CHIẾN THẮNG!" if won else "KẾT THÚC TRÒ CHƠI!")
        txt_title = FONT_LG.render(msg, True, (255, 255, 255))
        txt_score = FONT_MD.render(f"Điểm số: {score}", True, (255, 255, 255))
        txt_sub = FONT_SM.render("Nhấn phím R để chơi lại hoặc P để tiếp tục", True, (148, 163, 184))

        screen.blit(txt_title, (WIDTH // 2 - txt_title.get_width() // 2, HEIGHT // 2 - 50))
        screen.blit(txt_score, (WIDTH // 2 - txt_score.get_width() // 2, HEIGHT // 2))
        screen.blit(txt_sub, (WIDTH // 2 - txt_sub.get_width() // 2, HEIGHT // 2 + 50))

    pygame.display.flip()


def shoot():
    global projectile
    if projectile or game_over or won or paused:
        return
    mx, my = pygame.mouse.get_pos()
    dx, dy = mx - SHOOTER["x"], my - SHOOTER["y"]
    if dy >= -20:
        return
    length = math.hypot(dx, dy) or 1
    projectile = {
        "x": SHOOTER["x"],
        "y": SHOOTER["y"] - 35,
        "vx": (dx / length) * 14,
        "vy": (dy / length) * 14,
        "color": current_color,
    }


# --- Vòng lặp chính của trò chơi ---
reset_game()

while True:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                shoot()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                reset_game()
            elif event.key == pygame.K_p:
                if not game_over and not won:
                    paused = not paused

    if not paused and not game_over and not won:
        update_projectile()

    draw_game()
