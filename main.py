import pygame
import sys
import random
import heapq
import pytmx
import xml.etree.ElementTree as ET

# Khởi tạo Pygame
pygame.init()

# Cài đặt màn hình trước khi load bản đồ
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Thief's Escape with Vision Zones")

# Load bản đồ Tiled sau khi đã khởi tạo màn hình
tmx_data = pytmx.load_pygame("map/5.tmx")  # Đường dẫn tới file .tmx
GRID_SIZE = tmx_data.tilewidth  # Kích thước ô (giả sử tilewidth = tileheight)
ROWS = tmx_data.height  # Số hàng
COLS = tmx_data.width   # Số cột

# Tính toán kích thước bản đồ gốc (pixel)
MAP_WIDTH = COLS * GRID_SIZE
MAP_HEIGHT = ROWS * GRID_SIZE

# Tính hệ số phóng to để bản đồ lấp đầy màn hình
scale_factor = min(SCREEN_WIDTH / MAP_WIDTH, SCREEN_HEIGHT / MAP_HEIGHT)  # Phóng to vừa đủ để lấp đầy màn hình
SCALED_GRID_SIZE = GRID_SIZE * scale_factor  # Kích thước ô sau khi phóng to

# Căn giữa bản đồ
OFFSET_X = (SCREEN_WIDTH - MAP_WIDTH * scale_factor) // 2
OFFSET_Y = (SCREEN_HEIGHT - MAP_HEIGHT * scale_factor) // 2

# Màu sắc
WHITE = (255, 255, 255)  # Sàn/lối ra
BLACK = (0, 0, 0)  # Tường
RED = (255, 0, 0)  # Nhân vật trộm (dùng làm mặc định nếu lỗi)
GREEN = (0, 255, 0)  # Vật phẩm
BLUE = (0, 0, 255)  # Ông chủ
GRAY = (128, 128, 128)  # Màu nền
LIGHT_BLUE = (135, 206, 250)  # Viền của vùng tầm nhìn nhân vật trộm
LIGHT_PURPLE = (147, 112, 219)  # Viền của vùng tầm nhìn ông chủ
YELLOW = (255, 255, 0)  # Màu viền cho các đối tượng nội thất

# Font để hiển thị debug
font = pygame.font.SysFont(None, 30)

# Tạo lưới từ lớp "Wall" (chỉ đánh dấu tường)
map_grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]

# Đánh dấu các ô tường từ layer "Wall"
wall_layer = tmx_data.get_layer_by_name("Wall")
for x in range(COLS):
    for y in range(ROWS):
        if wall_layer.data[y][x] != 0:  # Nếu có tile trong lớp Wall
            map_grid[y][x] = 1

# Lưu danh sách hình chữ nhật bao quanh của đồ nội thất
furniture_rects = []

# Tạo danh sách hình chữ nhật bao quanh của đồ nội thất từ layer "FurnitureObjects"
furniture_layer = tmx_data.get_layer_by_name("FurnitureObjects")
for obj in furniture_layer:
    if hasattr(obj, 'x') and hasattr(obj, 'y') and hasattr(obj, 'width') and hasattr(obj, 'height'):
        # Tính hình chữ nhật bao quanh của đồ nội thất (sau khi phóng to)
        scaled_width = obj.width * scale_factor
        scaled_height = obj.height * scale_factor
        tile_width_in_grids = obj.width / GRID_SIZE
        tile_height_in_grids = obj.height / GRID_SIZE
        offset_x = (SCALED_GRID_SIZE * tile_width_in_grids - scaled_width) / 2
        offset_y = (SCALED_GRID_SIZE * tile_height_in_grids - scaled_height) / 2
        draw_x = obj.x * scale_factor + OFFSET_X + offset_x
        draw_y = obj.y * scale_factor + OFFSET_Y + offset_y
        furniture_rect = pygame.Rect(draw_x, draw_y, scaled_width, scaled_height)
        furniture_rects.append(furniture_rect)

# Load vị trí từ lớp "Objects"
thief_pos = None
master_pos = None
items = []
exit_pos = None

# Tìm kiếm đối tượng dựa trên Name
for obj in tmx_data.objects:
    if obj.name == "thief":
        thief_pos = [int(obj.y // GRID_SIZE), int(obj.x // GRID_SIZE)]
    elif obj.name == "master":
        master_pos = [int(obj.y // GRID_SIZE), int(obj.x // GRID_SIZE)]
    elif obj.name == "item":
        items.append([int(obj.y // GRID_SIZE), int(obj.x // GRID_SIZE)])
    elif obj.name == "exit":
        exit_pos = [int(obj.y // GRID_SIZE), int(obj.x // GRID_SIZE)]

# Hàm tính hitbox của nhân vật
def get_character_hitbox(pos, size):
    draw_x = pos[1] * SCALED_GRID_SIZE + OFFSET_X
    draw_y = pos[0] * SCALED_GRID_SIZE + OFFSET_Y
    return pygame.Rect(draw_x, draw_y, size, size)

# Hàm kiểm tra va chạm với đồ nội thất
def check_furniture_collision(pos, size, furniture_rects):
    character_rect = get_character_hitbox(pos, size)
    # Kiểm tra va chạm với từng đồ nội thất
    for furniture_rect in furniture_rects:
        if character_rect.colliderect(furniture_rect):
            return True
    return False

# Hàm tìm vị trí gần nhất không va chạm
def find_nearest_free_position(start_pos, size, furniture_rects, grid):
    if not check_furniture_collision(start_pos, size, furniture_rects):
        return start_pos  # Vị trí hiện tại không va chạm
    
    # Sử dụng BFS để tìm vị trí gần nhất không va chạm
    queue = [(start_pos[0], start_pos[1])]
    visited = {(start_pos[0], start_pos[1])}
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    
    while queue:
        row, col = queue.pop(0)
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            new_pos = [new_row, new_col]
            if (0 <= new_row < ROWS and 0 <= new_col < COLS and 
                (new_row, new_col) not in visited and 
                grid[new_row][new_col] != 1 and 
                not check_furniture_collision(new_pos, size, furniture_rects)):
                return new_pos
            if 0 <= new_row < ROWS and 0 <= new_col < COLS and (new_row, new_col) not in visited:
                visited.add((new_row, new_col))
                queue.append((new_row, new_col))
    
    # Nếu không tìm thấy vị trí nào, trả về vị trí mặc định
    print("Warning: Could not find a free position!")
    return [1, 1]

# Gán giá trị mặc định nếu không tìm thấy và kiểm tra va chạm
if thief_pos is None:
    print("Warning: Thief position not found in the map! Using default position.")
    thief_pos = [1, 1]  # Vị trí mặc định
else:
    # Kiểm tra và điều chỉnh vị trí khởi tạo của thief
    thief_pos = find_nearest_free_position(thief_pos, SCALED_GRID_SIZE, furniture_rects, map_grid)

if master_pos is None:
    print("Warning: Master position not found in the map! Using default position.")
    master_pos = [5, 5]
else:
    # Kiểm tra và điều chỉnh vị trí khởi tạo của master
    master_pos = find_nearest_free_position(master_pos, SCALED_GRID_SIZE, furniture_rects, map_grid)

if exit_pos is None:
    print("Warning: Exit position not found in the map! Using default position.")
    exit_pos = [10, 10]
if not items:
    print("Warning: No items found in the map! Adding default item.")
    items.append([3, 3])

# Load sprite sheet cho nhân vật thief
try:
    thief_sprite_sheet = pygame.image.load("Player.png")  # Đường dẫn tới sprite sheet
except pygame.error as e:
    print(f"Error loading thief sprite sheet: {e}")
    # Nếu không tải được sprite sheet, dùng hình vuông màu đỏ làm mặc định
    thief_sprite_sheet = pygame.Surface((SCALED_GRID_SIZE * 4, SCALED_GRID_SIZE * 4))
    thief_sprite_sheet.fill(RED)

# Cắt sprite sheet thành các hình ảnh riêng lẻ
SPRITE_ROWS = 4  # Số hàng trong sprite sheet
SPRITE_COLS = 4  # Số cột trong sprite sheet
sprite_width = thief_sprite_sheet.get_width() // SPRITE_COLS  # Chiều rộng của mỗi sprite
sprite_height = thief_sprite_sheet.get_height() // SPRITE_ROWS  # Chiều cao của mỗi sprite

THIEF_SCALE_FACTOR = 1.0  # Hệ số phóng to cho nhân vật thief
THIEF_SIZE = int(SCALED_GRID_SIZE * THIEF_SCALE_FACTOR)
MASTER_SIZE = THIEF_SIZE  # Đặt kích thước hitbox của master bằng với thief

# Từ điển lưu các hình ảnh theo hướng
thief_sprites = {
    "down": [],
    "up": [],
    "left": [],
    "right": []
}

# Cắt sprite sheet và lưu vào từ điển
for row in range(SPRITE_ROWS):
    for col in range(SPRITE_COLS):
        # Cắt hình ảnh nhỏ từ sprite sheet
        sprite_rect = pygame.Rect(col * sprite_width, row * sprite_height, sprite_width, sprite_height)
        sprite_image = thief_sprite_sheet.subsurface(sprite_rect)
        # Phóng to hình ảnh để phù hợp với SCALED_GRID_SIZE
        sprite_image = pygame.transform.scale(sprite_image, (THIEF_SIZE, THIEF_SIZE))
        # Lưu vào từ điển theo hướng
        if col == 0:  # Cột 1: Đi xuống
            thief_sprites["down"].append(sprite_image)
        elif col == 1:  # Cột 2: Đi lên
            thief_sprites["up"].append(sprite_image)
        elif col == 2:  # Cột 3: Sang trái
            thief_sprites["left"].append(sprite_image)
        elif col == 3:  # Cột 4: Sang phải
            thief_sprites["right"].append(sprite_image)

# Sprite đơn giản (phóng to theo scale_factor) cho các đối tượng khác
master_img = pygame.Surface((MASTER_SIZE, MASTER_SIZE))  # Sử dụng MASTER_SIZE cho hình ảnh của master
master_img.fill(BLUE)
item_img = pygame.Surface((SCALED_GRID_SIZE, SCALED_GRID_SIZE))
item_img.fill(GREEN)
exit_img = pygame.Surface((SCALED_GRID_SIZE, SCALED_GRID_SIZE))
exit_img.fill(WHITE)

# Tầm nhìn
THIEF_VISION_RANGE = 2
MASTER_VISION_RANGE = 3

# Hướng mặc định của nhân vật trộm
thief_direction = "right"

# Tạo zone tầm nhìn của nhân vật trộm
def create_thief_vision_zone(thief_pos, direction):
    row, col = thief_pos
    vision_range = THIEF_VISION_RANGE
    zone = set()

    for i in range(max(0, row - 1), min(ROWS, row + 2)):
        for j in range(max(0, col - 1), min(COLS, col + 2)):
            if abs(i - row) + abs(j - col) <= 1:
                zone.add((i, j))

    if direction == "up":
        for i in range(max(0, row - vision_range), row + 1):
            width = vision_range - abs(i - row)
            for j in range(max(0, col - width), min(COLS, col + width + 1)):
                zone.add((i, j))
    elif direction == "down":
        for i in range(row, min(ROWS, row + vision_range + 1)):
            width = vision_range - abs(i - row)
            for j in range(max(0, col - width), min(COLS, col + width + 1)):
                zone.add((i, j))
    elif direction == "left":
        for j in range(max(0, col - vision_range), col + 1):
            height = vision_range - abs(j - col)
            for i in range(max(0, row - height), min(ROWS, row + height + 1)):
                zone.add((i, j))
    elif direction == "right":
        for j in range(col, min(COLS, col + vision_range + 1)):
            height = vision_range - abs(j - col)
            for i in range(max(0, row - height), min(ROWS, row + height + 1)):
                zone.add((i, j))
    return zone

# Tạo zone tầm nhìn của ông chủ (hình tròn)
def create_master_vision_zone(master_pos):
    row, col = master_pos
    vision_range = MASTER_VISION_RANGE
    zone = set()

    for i in range(max(0, row - vision_range), min(ROWS, row + vision_range + 1)):
        for j in range(max(0, col - vision_range), min(COLS, col + vision_range + 1)):
            if abs(i - row) + abs(j - col) <= vision_range:
                zone.add((i, j))
    return zone

# Kiểm tra nhân vật trộm có trong tầm nhìn của ông chủ không
def master_vision(master_pos, thief_pos):
    zone = create_master_vision_zone(master_pos)
    return (thief_pos[0], thief_pos[1]) in zone

# Thuật toán A* tìm đường, có kiểm tra va chạm với đồ nội thất
def a_star(start, goal, grid, character_size, furniture_rects):
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    if start is None or goal is None:
        print("Error: Start or goal position is None!")
        return None
    
    # Nếu vị trí hiện tại va chạm, tìm vị trí gần nhất không va chạm
    adjusted_start = find_nearest_free_position(start, character_size, furniture_rects, grid)
    if adjusted_start != start:
        print(f"Adjusted start position from {start} to {adjusted_start}")
        start = adjusted_start

    pq = [(0 + heuristic(start, goal), 0, [start])]
    visited = {tuple(start): 0}
    while pq:
        _, cost, path = heapq.heappop(pq)
        x, y = path[-1]
        if [x, y] == goal:
            return path
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            next_x, next_y = x + dx, y + dy
            next_pos = [next_x, next_y]
            new_cost = cost + 1
            # Kiểm tra giới hạn bản đồ, tường, và va chạm với đồ nội thất
            if (0 <= next_x < len(grid) and 0 <= next_y < len(grid[0]) and 
                grid[next_x][next_y] != 1 and 
                not check_furniture_collision(next_pos, character_size, furniture_rects) and 
                (tuple(next_pos) not in visited or new_cost < visited[tuple(next_pos)])):
                visited[tuple(next_pos)] = new_cost
                priority = new_cost + heuristic(next_pos, goal)
                heapq.heappush(pq, (priority, new_cost, path + [next_pos]))
    return None

# AI cho ông chủ
def master_patrol(master_pos, waypoints):
    if not waypoints:
        while True:
            new_waypoint = [random.randint(1, ROWS-2), random.randint(1, COLS-2)]
            if map_grid[new_waypoint[0]][new_waypoint[1]] == 0:
                waypoints.append(new_waypoint)
                break
    return a_star(master_pos, waypoints[0], map_grid, MASTER_SIZE, furniture_rects)

def master_chase(master_pos, thief_pos):
    return a_star(master_pos, thief_pos, map_grid, MASTER_SIZE, furniture_rects)

def get_raw_gids_from_tmx(tmx_file_path):
    tree = ET.parse(tmx_file_path)
    root = tree.getroot()
    gid_map = {}
    for objgroup in root.findall(".//objectgroup[@name='FurnitureObjects']/object"):
        obj_id = int(objgroup.get("id"))
        gid = int(objgroup.get("gid", 0))
        gid_map[obj_id] = gid
    return gid_map

# Vẽ bản đồ từ Tiled với phóng to
def draw_map(screen, tmx_data, tmx_file_path="map/5.tmx"):
    # Đọc GID gốc từ file TMX
    raw_gids = get_raw_gids_from_tmx(tmx_file_path)

    # Vẽ các layer tile (như sàn, tường)
    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, image in layer.tiles():
                gid = layer.data[y][x]
                if gid == 0:
                    continue
                scaled_image = pygame.transform.scale(image, (int(SCALED_GRID_SIZE), int(SCALED_GRID_SIZE)))
                draw_x = x * SCALED_GRID_SIZE + OFFSET_X
                draw_y = y * SCALED_GRID_SIZE + OFFSET_Y
                screen.blit(scaled_image, (draw_x, draw_y))

    # Vẽ các đồ nội thất từ layer "FurnitureObjects" và tô viền
    furniture_layer = tmx_data.get_layer_by_name("FurnitureObjects")
    for obj in furniture_layer:
        if not hasattr(obj, 'image') or not obj.image:
            continue

        # Lấy GID của đối tượng từ pytmx
        gid = obj.gid if hasattr(obj, 'gid') else 0
        if gid == 0:
            continue

        # Lấy GID gốc từ file TMX
        obj_id = int(obj.id)
        raw_gid = raw_gids.get(obj_id, gid)  # Sử dụng GID từ TMX nếu có, nếu không thì dùng GID từ pytmx
        gid = int(raw_gid)

        # Giải mã GID để lấy thông tin lật và xoay
        FLIP_HORIZONTAL = 1 << 31  # Bit 31: Lật ngang
        FLIP_VERTICAL = 1 << 30    # Bit 30: Lật dọc
        FLIP_DIAGONAL = 1 << 29    # Bit 29: Xoay 90 độ (kết hợp lật)

        # Kiểm tra cờ lật và chuyển thành True/False
        flip_x = bool(gid & FLIP_HORIZONTAL)
        flip_y = bool(gid & FLIP_VERTICAL)
        flip_diagonal = bool(gid & FLIP_DIAGONAL)
        real_gid = gid & ~(FLIP_HORIZONTAL | FLIP_VERTICAL | FLIP_DIAGONAL)

        # Lấy hình ảnh gốc và chuyển đổi định dạng
        image = obj.image.convert_alpha()  # Đảm bảo bề mặt tương thích với Pygame

        # Lấy kích thước của đối tượng
        tile_width = obj.width if hasattr(obj, 'width') else GRID_SIZE
        tile_height = obj.height if hasattr(obj, 'height') else GRID_SIZE

        # Tính kích thước sau khi phóng to
        scaled_width = tile_width * scale_factor
        scaled_height = tile_height * scale_factor

        # Tính số ô mà tile chiếm (dựa trên kích thước gốc)
        tile_width_in_grids = tile_width / GRID_SIZE
        tile_height_in_grids = tile_height / GRID_SIZE

        # Điều chỉnh vị trí vẽ để căn giữa tile trong không gian của nó
        offset_x = (SCALED_GRID_SIZE * tile_width_in_grids - scaled_width) / 2
        offset_y = (SCALED_GRID_SIZE * tile_height_in_grids - scaled_height) / 2

        # Phóng to hình ảnh của đối tượng
        scaled_image = pygame.transform.scale(image, (int(scaled_width), int(scaled_height)))

        # Áp dụng lật (flip) trước khi xoay
        if flip_x:
            scaled_image = pygame.transform.flip(scaled_image, True, False)  # Lật ngang
        if flip_y:
            scaled_image = pygame.transform.flip(scaled_image, False, True)  # Lật dọc

        # Xoay hình ảnh nếu đối tượng có thuộc tính rotation
        rotation = getattr(obj, 'rotation', 0)
        if rotation != 0:
            scaled_image = pygame.transform.rotate(scaled_image, -rotation)  # Pygame xoay ngược chiều kim đồng hồ

        # Tính vị trí vẽ
        draw_x = obj.x * scale_factor + OFFSET_X + offset_x
        draw_y = obj.y * scale_factor + OFFSET_Y + offset_y

        # Điều chỉnh vị trí vẽ sau khi xoay
        if rotation != 0:
            rotated_rect = scaled_image.get_rect(center=(draw_x + scaled_width / 2, draw_y + scaled_height / 2))
            draw_x = rotated_rect.x
            draw_y = rotated_rect.y

        # Vẽ đối tượng
        screen.blit(scaled_image, (draw_x, draw_y))

        # # Tô viền cho đối tượng
        # pygame.draw.rect(screen, YELLOW, 
        #                  (draw_x, draw_y, scaled_width, scaled_height), 
        #                  width=3)

# Vòng lặp chính
clock = pygame.time.Clock()
collected_items = 0
path = None
master_waypoints = []
master_path = None
game_over = False

# Biến để chọn khung hình (frame) cho hoạt hình (hiện tại dùng frame đầu tiên)
current_frame = 0  # Dùng frame đầu tiên của mỗi hướng

while not game_over:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Tìm mục tiêu cho nhân vật trộm
    if collected_items < len(items):
        path = a_star(thief_pos, items[collected_items], map_grid, THIEF_SIZE, furniture_rects)
    else:
        path = a_star(thief_pos, exit_pos, map_grid, THIEF_SIZE, furniture_rects)

    # Di chuyển nhân vật trộm và cập nhật hướng
    if path and len(path) > 1:
        next_pos = path[1]
        # Kiểm tra va chạm với đồ nội thất trước khi di chuyển (để chắc chắn)
        if not check_furniture_collision(next_pos, THIEF_SIZE, furniture_rects):
            dx = next_pos[0] - thief_pos[0]
            dy = next_pos[1] - thief_pos[1]
            if dx == -1:
                thief_direction = "up"
            elif dx == 1:
                thief_direction = "down"
            elif dy == -1:
                thief_direction = "left"
            elif dy == 1:
                thief_direction = "right"
            
            thief_pos = next_pos
            path.pop(0)

            if thief_pos in items:
                items.remove(thief_pos)
                collected_items += 1
            if thief_pos == exit_pos and collected_items == len(items):
                print("Tên trộm đã thoát!")
                game_over = True
        else:
            # Nếu có va chạm, tìm đường mới
            path = None

    # Di chuyển ông chủ
    if master_vision(master_pos, thief_pos):
        master_path = master_chase(master_pos, thief_pos)
    else:
        if not master_path or len(master_path) <= 1:
            master_path = master_patrol(master_pos, master_waypoints)
        if master_path and master_waypoints and master_pos == master_waypoints[0]:
            master_waypoints.pop(0)

    if master_path and len(master_path) > 1:
        next_pos = master_path[1]
        # Kiểm tra va chạm với đồ nội thất trước khi di chuyển (để chắc chắn)
        if not check_furniture_collision(next_pos, MASTER_SIZE, furniture_rects):
            master_pos = next_pos
            master_path.pop(0)
        else:
            # Nếu có va chạm, tìm đường mới
            master_path = None

    if master_pos == thief_pos:
        print("Bị ông chủ bắt!")
        game_over = True

    # Vẽ game
    screen.fill(GRAY)  # Màu nền
    draw_map(screen, tmx_data)

    # Vẽ zone tầm nhìn của nhân vật trộm (chỉ vẽ viền)
    thief_vision_zone = create_thief_vision_zone(thief_pos, thief_direction)
    for i, j in thief_vision_zone:
        pygame.draw.rect(screen, LIGHT_BLUE, (j * SCALED_GRID_SIZE + OFFSET_X, i * SCALED_GRID_SIZE + OFFSET_Y, SCALED_GRID_SIZE, SCALED_GRID_SIZE), width=2)

    # Vẽ zone tầm nhìn của ông chủ (chỉ vẽ viền)
    master_vision_zone = create_master_vision_zone(master_pos)
    for i, j in master_vision_zone:
        pygame.draw.rect(screen, LIGHT_PURPLE, (j * SCALED_GRID_SIZE + OFFSET_X, i * SCALED_GRID_SIZE + OFFSET_Y, SCALED_GRID_SIZE, SCALED_GRID_SIZE), width=2)

    # Tính và in hitbox của nhân vật
    thief_hitbox = get_character_hitbox(thief_pos, THIEF_SIZE)
    master_hitbox = get_character_hitbox(master_pos, MASTER_SIZE)
    
    print(f"Thief hitbox: x={thief_hitbox.x}, y={thief_hitbox.y}, width={thief_hitbox.width}, height={thief_hitbox.height}")
    print(f"Master hitbox: x={master_hitbox.x}, y={master_hitbox.y}, width={master_hitbox.width}, height={master_hitbox.height}")

    # Vẽ hitbox lên màn hình
    # pygame.draw.rect(screen, GREEN, thief_hitbox, width=2)  # Hitbox của thief (màu xanh lá)
    # pygame.draw.rect(screen, BLUE, master_hitbox, width=2)  # Hitbox của master (màu xanh dương)

    # Vẽ nhân vật trộm với sprite tương ứng với hướng
    thief_img = thief_sprites[thief_direction][current_frame]  # Chọn sprite theo hướng
    screen.blit(thief_img, (thief_pos[1] * SCALED_GRID_SIZE + OFFSET_X, thief_pos[0] * SCALED_GRID_SIZE + OFFSET_Y))

    # Vẽ các đối tượng khác
    screen.blit(master_img, (master_pos[1] * SCALED_GRID_SIZE + OFFSET_X, master_pos[0] * SCALED_GRID_SIZE + OFFSET_Y))
    for item in items:
        screen.blit(item_img, (item[1] * SCALED_GRID_SIZE + OFFSET_X, item[0] * SCALED_GRID_SIZE + OFFSET_Y))
    screen.blit(exit_img, (exit_pos[1] * SCALED_GRID_SIZE + OFFSET_X, exit_pos[0] * SCALED_GRID_SIZE + OFFSET_Y))

    # Hiển thị trạng thái debug
    mode = "Đuổi theo" if master_vision(master_pos, thief_pos) else "Tuần tra"
    master_status = f"Ông chủ: {master_pos}, Chế độ: {mode}, Hướng trộm: {thief_direction}"
    status_text = font.render(master_status, True, BLACK)
    screen.blit(status_text, (10, 10))

    # Cập nhật màn hình
    pygame.display.flip()
    clock.tick(5)  # Tốc độ chậm để dễ quan sát

pygame.quit()
