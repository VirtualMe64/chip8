import pygame

MEMORY_SIZE = 4096 # memory size in bytes
ROM_START = 512
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

KEYCODES = [
    pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3,
    pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r,
    pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_f,
    pygame.K_z, pygame.K_x, pygame.K_c, pygame.K_v,
]

FPS = 60
INSTRUCTIONS_PER_FRAME = 12

class Chip8:
    memory = [0 for _ in range(MEMORY_SIZE)]
    stack = []
    pc = ROM_START

    screen_data = [[False for _ in range(DISPLAY_SIZE[0])] for _ in range(DISPLAY_SIZE[1])]

    delay_timer = 0
    sound_timer = 0
    i_register = 0
    registers = [0 for _ in range(REGISTER_COUNT)]

    def __init__(self, rom_path):
        # store font sprites
        for i in range(len(FONT_DATA)):
            self.memory[FONT_DATA_POINTER + i] = FONT_DATA[i]
        self.load_rom(rom_path)

        # create screen and start main loop
        self.screen = pygame.display.set_mode((
            DISPLAY_SIZE[0] * DISPLAY_PIXEL_WIDTH,
            DISPLAY_SIZE[1] * DISPLAY_PIXEL_WIDTH
        ))
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
            clock.tick(60)

            # 1: update registers
            if self.delay_timer > 0: self.delay_timer -= 1
            if self.sound_timer > 0: self.sound_timer -= 1

            for i in range(INSTRUCTIONS_PER_FRAME):
                # 2a: fetch instruction
                instruction = (self.memory[self.pc] << 8) + self.memory[self.pc + 1]
                self.pc += 2

                # 2b: decode and execute
                self.execute(instruction)

            # 3: display screen_data
            self.draw_screen()
            pygame.display.update()

    def execute(self, instruction):
        opcode = instruction >> 12  # first nibble, used to specify instruction
        x = (instruction >> 8) & 0xF # second nibble, used to index registers 
        y = (instruction >> 4) & 0xF # third nibble, used to index registers
        n = instruction & 0xF # fourth nibble
        nn = instruction & 0xFF # second byte
        nnn = instruction & 0xFFF # last 3 nibbles
        
        match opcode:
            case 0:
                if opcode == 0x00E0: # clear screen
                    self.screen_data = [[False for _ in range(DISPLAY_SIZE[0])] for _ in range(DISPLAY_SIZE[1])]
            case 1: # jump to nnn
                self.pc = nnn
            case 6: # set register x to nn
                self.registers[x] = nn
            case 7: # add nn to register x
                self.registers[x] = (self.registers[x] + nn) % 256
            case 0xA: # set the index register to nnn
                self.i_register = nnn
            case 0xD: # draw an n pixel tall sprite from memory location I at x = register x, y = register y
                x_val = self.registers[x] % DISPLAY_SIZE[0]
                y_val = self.registers[y] % DISPLAY_SIZE[1]
                sprite_ptr = self.i_register
                
                for row in range(n):
                    byte = self.memory[sprite_ptr + row]
                    for offset in range(8):
                        x_pixel = x_val + 7 - offset
                        y_pixel = y_val + row

                        if x_pixel >= DISPLAY_SIZE[0]: break
                        if y_pixel >= DISPLAY_SIZE[1]: break

                        
                        if byte % 2 == 1:
                            curr = self.screen_data[y_pixel][x_pixel]
                            if curr: # set flag register if pixels turned off
                                self.registers[-1] = 1
                            self.screen_data[y_pixel][x_pixel] = not curr
                        byte >>= 1

            case _:
                print(f"Unknown instruction 0x{hex(opcode)[2:]}{hex(x)[2:]}{hex(y)[2:]}{hex(n)[2:]}")

    def load_rom(self, path):
        with open(path, 'rb') as rom:
            idx = ROM_START
            while (byte := rom.read(1)):
                self.memory[idx] = int.from_bytes(byte)
                idx += 1

    def draw_screen(self):
        for col in range(DISPLAY_SIZE[0]):
            for row in range(DISPLAY_SIZE[1]):
                color = COLOR_1 if self.screen_data[row][col] else COLOR_0
                x = col * DISPLAY_PIXEL_WIDTH
                y = row * DISPLAY_PIXEL_WIDTH
                pygame.draw.rect(self.screen, color, [x, y, x + DISPLAY_PIXEL_WIDTH, y + DISPLAY_PIXEL_WIDTH])

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Error: must specify a ROM to load")
        sys.exit(1)
    
    test = Chip8(sys.argv[1])