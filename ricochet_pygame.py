import pygame
import sys
import copy
import random
from collections import deque

class RicochetRobotsPygame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("碰撞機器人 (Ricochet Robots) - 隨機生成版 + 智能提示")
        
        self.width = 16
        self.height = 16
        self.cell_size = 40
        self.margin_top = 60
        self.margin_bottom = 100
        self.offset_x = 0

        screen_width = self.width * self.cell_size
        screen_height = self.height * self.cell_size + self.margin_top + self.margin_bottom
        self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)

        self._font_path = pygame.font.match_font(
            'stheitilight,arialunicode,pingfanghk,microsoftjhonghei,simhei,'
            'notosanscjk,notosanscjktc,notosanscjksc,notosansctc,'
            'wqyzenhei,wqymicrohei,droidsansfallback,unifont'
        )
        if not self._font_path:
            print("警告：找不到合適的中文系統字體，文字可能無法正確顯示。")
        self._on_resize(*self.screen.get_size())
            
        self.colors = {
            'Red': (220, 50, 50),
            'Blue': (50, 100, 220),
            'Green': (50, 200, 50),
            'Yellow': (220, 200, 50),
            'Black': (40, 40, 40),
            'White': (245, 245, 245),
            'Gray': (200, 200, 200),
            'Highlight': (200, 255, 200),
            'Panel': (230, 230, 235)
        }
        
        self.calculating = False
        self.optimal_steps = -1
        self.solution_path = []
        self.show_hint = False
        self.show_optimal_steps = False
        
        self.generate_random_board()

    def _load_fonts(self):
        size = max(14, self.cell_size // 2)
        title_size = max(16, self.cell_size // 2 + 4)
        if self._font_path:
            self.font = pygame.font.Font(self._font_path, size)
            self.title_font = pygame.font.Font(self._font_path, title_size)
        else:
            self.font = pygame.font.Font(None, size + 4)
            self.title_font = pygame.font.Font(None, title_size + 4)

    def _on_resize(self, w, h):
        # Two-case formula to avoid circular dependency:
        # cs >= 32: margins = cs*4, so total = cs*20 → cs = h//20
        # cs < 32:  margins fixed at 125,           → cs = (h-125)//16
        cs_h = h // 20
        if cs_h < 32:
            cs_h = (h - 125) // 16
        self.cell_size = max(20, min(w // self.width, cs_h))
        self.margin_top = max(45, int(self.cell_size * 1.5))
        self.margin_bottom = max(80, int(self.cell_size * 2.5))
        self.offset_x = (w - self.width * self.cell_size) // 2
        self._load_fonts()

    def generate_random_board(self):
        self.all_targets = []
        colors = ['Red', 'Blue', 'Green', 'Yellow'] * 4
        wall_types = ['TR', 'TL', 'BR', 'BL']
        
        used_pos = set()
        for x in range(7, 9):
            for y in range(7, 9):
                used_pos.add((x, y))
                
        for color in colors:
            while True:
                tx = random.randint(1, 14)
                ty = random.randint(1, 14)
                
                valid = True
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if (tx + dx, ty + dy) in used_pos:
                            valid = False
                            break
                    if not valid: break
                
                if valid:
                    used_pos.add((tx, ty))
                    w_type = random.choice(wall_types)
                    self.all_targets.append((color, tx, ty, w_type))
                    break

        self.extra_h_walls = []
        self.extra_v_walls = []
        for _ in range(8):
            if random.choice([True, False]):
                x = random.randint(2, 13)
                y = random.choice([1, 15])
                self.extra_v_walls.append((x, y))
            else:
                x = random.choice([1, 15])
                y = random.randint(2, 13)
                self.extra_h_walls.append((x, y))

        self.initial_robots = {}
        r_colors = ['Red', 'Blue', 'Green', 'Yellow']
        for c in r_colors:
            while True:
                rx = random.randint(0, 15)
                ry = random.randint(0, 15)
                if (rx, ry) not in used_pos:
                    used_pos.add((rx, ry))
                    self.initial_robots[c] = [rx, ry]
                    break

        self.setup_walls()
        self.select_next_target()

    def setup_walls(self):
        self.h_walls = [[False] * self.width for _ in range(self.height)]
        self.v_walls = [[False] * self.width for _ in range(self.height)]
        
        for x in range(self.width): self.h_walls[0][x] = True
        for y in range(self.height): self.v_walls[y][0] = True
            
        self.h_walls[7][7] = True; self.h_walls[7][8] = True
        self.h_walls[9][7] = True; self.h_walls[9][8] = True
        self.v_walls[7][7] = True; self.v_walls[8][7] = True
        self.v_walls[7][9] = True; self.v_walls[8][9] = True
        
        for x, y in self.extra_v_walls:
            if y == 1: self.v_walls[0][x] = True
            else: self.v_walls[15][x] = True
            
        for x, y in self.extra_h_walls:
            if x == 1: self.h_walls[y][0] = True
            else: self.h_walls[y][15] = True

        for color, x, y, walls in self.all_targets:
            if 'T' in walls: self.h_walls[y][x] = True
            if 'B' in walls: self.h_walls[y+1][x] = True
            if 'L' in walls: self.v_walls[y][x] = True
            if 'R' in walls: self.v_walls[y][x+1] = True

    def select_next_target(self):
        self.current_target = random.choice(self.all_targets)
        self.moves = 0
        self.won = False
        self.robots = copy.deepcopy(self.initial_robots)
        self.selected_robot = None
        self.show_hint = False
        self.show_optimal_steps = False
        self.optimal_steps = -1
        self.solution_path = []
        self.calculating = True 

    def solve_bfs(self):
        tc, tx, ty, _ = self.current_target
        colors = ['Red', 'Blue', 'Green', 'Yellow']
        color_zh = ['紅', '藍', '綠', '黃']
        target_idx = colors.index(tc)
        target_pos = (tx, ty)
        
        start_state = tuple(tuple(self.initial_robots[c]) for c in colors)
        
        queue = deque([(start_state, [])])
        visited = set([start_state])
        
        directions = [(0, -1, '上'), (0, 1, '下'), (-1, 0, '左'), (1, 0, '右')]
        max_depth = 20 
        max_states = 100000
        
        while queue:
            if len(visited) > max_states:
                break
                
            state, path = queue.popleft()
            
            if len(path) >= max_depth:
                continue
                
            for i, c in enumerate(colors):
                for dx, dy, d_name in directions:
                    curr_x, curr_y = state[i]
                    other_robots = set(state[j] for j in range(4) if j != i)
                    
                    while True:
                        if dx == 1:
                            if curr_x + 1 >= self.width or self.v_walls[curr_y][curr_x + 1]: break
                        elif dx == -1:
                            if curr_x <= 0 or self.v_walls[curr_y][curr_x]: break
                        elif dy == 1:
                            if curr_y + 1 >= self.height or self.h_walls[curr_y + 1][curr_x]: break
                        elif dy == -1:
                            if curr_y <= 0 or self.h_walls[curr_y][curr_x]: break
                            
                        test_x, test_y = curr_x + dx, curr_y + dy
                        if 7 <= test_x <= 8 and 7 <= test_y <= 8: break
                        if (test_x, test_y) in other_robots: break
                        
                        curr_x, curr_y = test_x, test_y
                        
                    if (curr_x, curr_y) != state[i]:
                        new_state = list(state)
                        new_state[i] = (curr_x, curr_y)
                        new_state = tuple(new_state)
                        
                        if new_state not in visited:
                            new_path = path + [(color_zh[i], d_name)]
                            
                            if i == target_idx and (curr_x, curr_y) == target_pos:
                                self.solution_path = new_path
                                self.optimal_steps = len(new_path)
                                return
                            
                            visited.add(new_state)
                            queue.append((new_state, new_path))
                            
        self.optimal_steps = -1
        self.solution_path = []

    def get_color_name(self, color_key):
        return {'Red': '紅', 'Blue': '藍', 'Green': '綠', 'Yellow': '黃'}.get(color_key, color_key)

    def draw(self):
        self.screen.fill(self.colors['White'])

        cs = self.cell_size
        offset_x = self.offset_x
        offset_y = self.margin_top
        grid_w = self.width * cs
        grid_h = self.height * cs

        # Top and bottom panel bands
        screen_w, screen_h = self.screen.get_size()
        pygame.draw.rect(self.screen, self.colors['Panel'], (0, 0, screen_w, offset_y))
        pygame.draw.rect(self.screen, self.colors['Panel'], (0, offset_y + grid_h, screen_w, screen_h - offset_y - grid_h))
        pygame.draw.line(self.screen, self.colors['Gray'], (0, offset_y), (screen_w, offset_y), 1)
        pygame.draw.line(self.screen, self.colors['Gray'], (0, offset_y + grid_h), (screen_w, offset_y + grid_h), 1)

        tc, tx, ty, _ = self.current_target
        target_color_zh = self.get_color_name(tc)

        if self.calculating:
            opt_str = "計算最佳解中..."
        elif self.show_optimal_steps:
            if self.optimal_steps != -1:
                opt_str = f"最佳解: {self.optimal_steps} 步"
            else:
                opt_str = "最佳解: 20步以上 (或無解)"
        else:
            opt_str = "最佳解: (點擊畫面顯示)"

        if self.won:
            msg = f"太棒了！共花 {self.moves} 步。按「空白鍵」下一關！"
            status_color = self.colors['Green']
        else:
            msg = f"目標：【{target_color_zh}色】到方塊處 (已走:{self.moves}步 | {opt_str})"
            status_color = self.colors['Black']

        text_surface = self.title_font.render(msg, True, status_color)
        title_h = text_surface.get_height()
        self.screen.blit(text_surface, (offset_x, (offset_y - title_h) // 2))

        for x in range(self.width):
            for y in range(self.height):
                rect = pygame.Rect(offset_x + x * cs, offset_y + y * cs, cs, cs)
                if 7 <= x <= 8 and 7 <= y <= 8:
                    pygame.draw.rect(self.screen, self.colors['Black'], rect)
                else:
                    cell_color = (238, 238, 230) if (x + y) % 2 == 0 else (248, 248, 242)
                    pygame.draw.rect(self.screen, cell_color, rect)
                pygame.draw.rect(self.screen, self.colors['Gray'], rect, 1)

        pulse = abs(__import__('math').sin(pygame.time.get_ticks() / 500)) * (cs // 8)
        inner = max(2, cs // 4 - int(pulse))
        target_rect = pygame.Rect(offset_x + tx * cs + inner, offset_y + ty * cs + inner, cs - inner * 2, cs - inner * 2)
        pygame.draw.rect(self.screen, self.colors[tc], target_rect, border_radius=max(2, inner))
        pygame.draw.rect(self.screen, self.colors['Black'], target_rect, 2, border_radius=max(2, inner))

        if self.selected_robot and not self.won:
            rx, ry = self.robots[self.selected_robot]
            sel_rect = pygame.Rect(offset_x + rx * cs, offset_y + ry * cs, cs, cs)
            pygame.draw.rect(self.screen, self.colors['Highlight'], sel_rect, 0)

        wall_thick = max(2, cs // 10)
        for y in range(self.height):
            for x in range(self.width):
                x0 = offset_x + x * cs
                y0 = offset_y + y * cs
                if self.h_walls[y][x] or y == 0:
                    pygame.draw.line(self.screen, self.colors['Black'], (x0, y0), (x0 + cs, y0), wall_thick)
                if self.v_walls[y][x] or x == 0:
                    pygame.draw.line(self.screen, self.colors['Black'], (x0, y0), (x0, y0 + cs), wall_thick)

        pygame.draw.line(self.screen, self.colors['Black'], (offset_x, offset_y + grid_h), (offset_x + grid_w, offset_y + grid_h), wall_thick)
        pygame.draw.line(self.screen, self.colors['Black'], (offset_x + grid_w, offset_y), (offset_x + grid_w, offset_y + grid_h), wall_thick)

        radius = max(5, cs // 2 - cs // 8)
        for name, pos in self.robots.items():
            rx, ry = pos
            center_x = offset_x + rx * cs + cs // 2
            center_y = offset_y + ry * cs + cs // 2
            pygame.draw.circle(self.screen, self.colors[name], (center_x, center_y), radius)
            pygame.draw.circle(self.screen, self.colors['Black'], (center_x, center_y), radius, 2)
            if name == self.selected_robot and not self.won:
                pygame.draw.circle(self.screen, self.colors['Black'], (center_x, center_y), radius + 2, 4)

        key_defs = [('↑↓←→', '移動'), ('R', '回原位'), ('H', '提示'), ('空白', '換目標'), ('N', '重生')]
        key_color = (60, 60, 80)
        bg_color  = (210, 210, 218)
        pad_x, pad_y = max(3, cs // 10), max(2, cs // 14)
        gap = pad_x * 3
        text_y = offset_y + grid_h + cs // 3

        # Pre-render to measure total width for centering
        rendered = [(self.font.render(k, True, key_color),
                     self.font.render(d, True, self.colors['Black'])) for k, d in key_defs]
        total_w = sum(ks.get_width() + pad_x * 2 + ds.get_width() for ks, ds in rendered) + gap * (len(rendered) - 1)
        kx = offset_x + (grid_w - total_w) // 2

        for key_surf, desc_surf in rendered:
            kw = key_surf.get_width() + pad_x * 2
            kh = key_surf.get_height() + pad_y * 2
            pygame.draw.rect(self.screen, bg_color,
                             pygame.Rect(kx, text_y, kw, kh), border_radius=max(2, cs // 16))
            pygame.draw.rect(self.screen, (150, 150, 165),
                             pygame.Rect(kx, text_y, kw, kh), 1, border_radius=max(2, cs // 16))
            self.screen.blit(key_surf, (kx + pad_x, text_y + pad_y))
            self.screen.blit(desc_surf, (kx + kw + pad_x, text_y + pad_y))
            kx += kw + desc_surf.get_width() + gap

        if self.show_hint:
            if self.optimal_steps != -1 and len(self.solution_path) > 0:
                sim_robots = copy.deepcopy(self.initial_robots)
                zh_to_color = {'紅': 'Red', '藍': 'Blue', '綠': 'Green', '黃': 'Yellow'}
                dir_map = {'上': (0, -1), '下': (0, 1), '左': (-1, 0), '右': (1, 0)}

                for step_idx, (color_zh, dir_name) in enumerate(self.solution_path):
                    robot_color = zh_to_color.get(color_zh)
                    if not robot_color: continue

                    dx, dy = dir_map.get(dir_name, (0, 0))
                    curr_x, curr_y = sim_robots[robot_color]

                    shift_unit = cs // 8
                    offset_shift = (step_idx % 3) * shift_unit - shift_unit
                    start_x = offset_x + curr_x * cs + cs // 2 + offset_shift
                    start_y = offset_y + curr_y * cs + cs // 2 + offset_shift

                    test_x, test_y = curr_x, curr_y
                    while True:
                        if dx == 1:
                            if test_x + 1 >= self.width or self.v_walls[test_y][test_x + 1]: break
                        elif dx == -1:
                            if test_x <= 0 or self.v_walls[test_y][test_x]: break
                        elif dy == 1:
                            if test_y + 1 >= self.height or self.h_walls[test_y + 1][test_x]: break
                        elif dy == -1:
                            if test_y <= 0 or self.h_walls[test_y][test_x]: break

                        next_x, next_y = test_x + dx, test_y + dy
                        if 7 <= next_x <= 8 and 7 <= next_y <= 8: break

                        collision = False
                        for c, pos in sim_robots.items():
                            if pos[0] == next_x and pos[1] == next_y:
                                collision = True
                                break
                        if collision: break

                        test_x, test_y = next_x, next_y

                    sim_robots[robot_color] = [test_x, test_y]

                    end_x = offset_x + test_x * cs + cs // 2 + offset_shift
                    end_y = offset_y + test_y * cs + cs // 2 + offset_shift

                    if (start_x, start_y) != (end_x, end_y):
                        pygame.draw.line(self.screen, self.colors[robot_color], (start_x, start_y), (end_x, end_y), max(2, cs // 10))

                        head_len = max(6, cs // 5)
                        if dx == 1:
                            pts = [(end_x, end_y), (end_x - head_len, end_y - head_len), (end_x - head_len, end_y + head_len)]
                        elif dx == -1:
                            pts = [(end_x, end_y), (end_x + head_len, end_y - head_len), (end_x + head_len, end_y + head_len)]
                        elif dy == 1:
                            pts = [(end_x, end_y), (end_x - head_len, end_y - head_len), (end_x + head_len, end_y - head_len)]
                        elif dy == -1:
                            pts = [(end_x, end_y), (end_x - head_len, end_y + head_len), (end_x + head_len, end_y + head_len)]
                        else:
                            pts = []

                        if pts:
                            pygame.draw.polygon(self.screen, self.colors[robot_color], pts)

                        mid_x = start_x + (end_x - start_x) * 0.7
                        mid_y = start_y + (end_y - start_y) * 0.7
                        step_r = max(7, cs // 4)
                        pygame.draw.circle(self.screen, self.colors['White'], (int(mid_x), int(mid_y)), step_r)
                        pygame.draw.circle(self.screen, self.colors['Black'], (int(mid_x), int(mid_y)), step_r, 1)
                        step_text = self.font.render(str(step_idx + 1), True, self.colors['Black'])
                        text_rect = step_text.get_rect(center=(int(mid_x), int(mid_y)))
                        self.screen.blit(step_text, text_rect)

            elif self.calculating:
                hint_str = "解答: 計算中..."
                hint_text = self.font.render(hint_str, True, self.colors['Blue'])
                self.screen.blit(hint_text, (offset_x, offset_y + grid_h + cs))
            else:
                hint_str = "解答: 20 步內無解 (地圖可能將目標封死，請按 N 重生)"
                hint_text = self.font.render(hint_str, True, self.colors['Blue'])
                self.screen.blit(hint_text, (offset_x, offset_y + grid_h + cs))

        pygame.display.flip()

    def get_robot_at(self, x, y):
        for name, pos in self.robots.items():
            if pos[0] == x and pos[1] == y:
                return name
        return None

    def handle_click(self, mouse_pos):
        if self.won or self.calculating: return

        mx, my = mouse_pos
        offset_x = self.offset_x
        offset_y = self.margin_top
        if my < offset_y or my > offset_y + self.height * self.cell_size: return
        if mx < offset_x or mx > offset_x + self.width * self.cell_size: return

        grid_x = (mx - offset_x) // self.cell_size
        grid_y = (my - offset_y) // self.cell_size

        clicked = self.get_robot_at(grid_x, grid_y)
        if clicked:
            self.selected_robot = clicked

    def move(self, dx, dy):
        if not self.selected_robot or self.won or self.calculating:
            return
            
        x, y = self.robots[self.selected_robot]
        start_x, start_y = x, y
        
        while True:
            if dx == 1:
                if x + 1 >= self.width or self.v_walls[y][x + 1]: break
            elif dx == -1:
                if x <= 0 or self.v_walls[y][x]: break
            elif dy == 1:
                if y + 1 >= self.height or self.h_walls[y + 1][x]: break
            elif dy == -1:
                if y <= 0 or self.h_walls[y][x]: break
                
            next_x, next_y = x + dx, y + dy
            if 7 <= next_x <= 8 and 7 <= next_y <= 8: break
            if self.get_robot_at(next_x, next_y): break
            x, y = next_x, next_y
            
        if x != start_x or y != start_y:
            self.robots[self.selected_robot] = [x, y]
            self.moves += 1
            
            tc, tx, ty, _ = self.current_target
            if self.selected_robot == tc and x == tx and y == ty:
                self.won = True
                self.selected_robot = None

    def run(self):
        clock = pygame.time.Clock()
        while True:
            if self.calculating:
                self.draw() 
                pygame.display.flip()
                self.solve_bfs() 
                if 4 <= self.optimal_steps <= 20:
                    self.calculating = False
                else:
                    self.generate_random_board()
                    self.select_next_target()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.VIDEORESIZE:  # pygame 1.x
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self._on_resize(event.w, event.h)
                elif hasattr(pygame, 'WINDOWRESIZED') and event.type == pygame.WINDOWRESIZED:  # pygame 2.x
                    w, h = self.screen.get_size()
                    self._on_resize(w, h)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.show_optimal_steps = True
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP: self.move(0, -1)
                    elif event.key == pygame.K_DOWN: self.move(0, 1)
                    elif event.key == pygame.K_LEFT: self.move(-1, 0)
                    elif event.key == pygame.K_RIGHT: self.move(1, 0)
                    elif event.key == pygame.K_h:
                        self.show_hint = not self.show_hint 
                    elif event.key == pygame.K_r:
                        self.robots = copy.deepcopy(self.initial_robots)
                        self.moves = 0
                        self.won = False
                        self.selected_robot = None
                    elif event.key == pygame.K_SPACE:
                        self.select_next_target()
                    elif event.key == pygame.K_n:
                        self.generate_random_board()

            self.draw()
            clock.tick(60)

if __name__ == "__main__":
    game = RicochetRobotsPygame()
    game.run()