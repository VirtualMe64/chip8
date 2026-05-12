import pygame

MEMORY_SIZE = 4096 # memory size in bytes
REGISTER_COUNT = 16

DISPLAY_SIZE = (64, 32)
DISPLAY_PIXEL_WIDTH = 10
COLOR_0 = (0, 0, 0)
COLOR_1 = (255, 255, 255)

FONT_DATA = [
    0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
    0x20, 0x60, 0x20, 0x20, 0x70, # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
    0x90, 0x90, 0xF0, 0x10, 0x10, # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
    0xF0, 0x10, 0x20, 0x40, 0x40, # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90, # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
    0xF0, 0x80, 0x80, 0x80, 0xF0, # C
    0xE0, 0x90, 0x90, 0x90, 0xE0, # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
    0xF0, 0x80, 0xF0, 0x80, 0x80  # F
]
FONT_DATA_POINTER = 0x50

class Chip8:
    memory = [0 for _ in range(MEMORY_SIZE)]
    stack = []
    pc = 0

    screen_data = [[False for _ in range(DISPLAY_SIZE[0])] for _ in range(DISPLAY_SIZE[1])]

    delay_timer = 0
    sound_timer = 0
    l_register = 0
    registers = [0 for _ in range(REGISTER_COUNT)]

    def __init__(self):
        # store font sprites
        for i in range(len(FONT_DATA)):
            self.memory[FONT_DATA_POINTER + i] = FONT_DATA[i]

        self.screen = pygame.display.set_mode((
            DISPLAY_SIZE[0] * DISPLAY_PIXEL_WIDTH,
            DISPLAY_SIZE[1] * DISPLAY_PIXEL_WIDTH
        ))

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
            
            # 1: update screen_data
            for n in range(16):
                font_offset = n * 5
                x_offset = 1 + (n % 8) * 5
                y_offset = 1 + (n // 8) * 6
                for i in range(5):
                    b = FONT_DATA[font_offset + i]
                    for j in range(8):
                        self.screen_data[y_offset + i][x_offset + (8 - j)] = b % 2 == 1
                        b >>= 1

            # 2: display screen_data
            self.draw_screen()
            pygame.display.update()
    
    def draw_screen(self):
        for col in range(DISPLAY_SIZE[0]):
            for row in range(DISPLAY_SIZE[1]):
                color = COLOR_1 if self.screen_data[row][col] else COLOR_0
                x = col * DISPLAY_PIXEL_WIDTH
                y = row * DISPLAY_PIXEL_WIDTH
                pygame.draw.rect(self.screen, color, [x, y, x + DISPLAY_PIXEL_WIDTH, y + DISPLAY_PIXEL_WIDTH])

if __name__ == "__main__":
    test = Chip8()