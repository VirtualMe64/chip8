import pygame
import random

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

# ambiguous opcodes
SET_SHIFT = False
JUMP_WITH_OFFSET_VX = False

class Processor:
    def __init__(self):
        self.memory = [0 for _ in range(MEMORY_SIZE)]
        self.stack = []
        self.pc = ROM_START

        self.screen_data = [[False for _ in range(DISPLAY_SIZE[0])] for _ in range(DISPLAY_SIZE[1])]

        self.delay_timer = 0
        self.sound_timer = 0
        self.i_register = 0
        self.registers = [0 for _ in range(REGISTER_COUNT)]

        # store font sprites
        for i in range(len(FONT_DATA)):
            self.memory[FONT_DATA_POINTER + i] = FONT_DATA[i]
        
    def load_rom(self, rom_data):
        for i in range(len(rom_data)):
            self.memory[ROM_START + i] = rom_data[i]

    def tick_timers(self):
        if self.delay_timer > 0: self.delay_timer -= 1
        if self.sound_timer > 0: self.sound_timer -= 1

    def fetch(self):
        instruction = (self.memory[self.pc] << 8) + self.memory[self.pc + 1]
        self.pc += 2
        return instruction

    def execute(self, instruction):
        def panic():
            print(f"Invalid instruction 0x{hex(opcode)[2:]}{hex(x)[2:]}{hex(y)[2:]}{hex(n)[2:]}")

        opcode = instruction >> 12  # first nibble, used to specify instruction
        x = (instruction >> 8) & 0xF # second nibble, used to index registers 
        y = (instruction >> 4) & 0xF # third nibble, used to index registers
        n = instruction & 0xF # fourth nibble
        nn = instruction & 0xFF # second byte
        nnn = instruction & 0xFFF # last 3 nibbles

        match opcode:
            case 0:
                if nn == 0xE0: # clear screen
                    self.screen_data = [[False for _ in range(DISPLAY_SIZE[0])] for _ in range(DISPLAY_SIZE[1])]
                if nn == 0xEE: # ret
                    self.pc = self.stack.pop()

            case 1: # jump to nnn
                self.pc = nnn

            case 2: # call subroutine
                self.stack.append(self.pc)
                self.pc = nnn

            case 3: # skip if register x equals nn
                if self.registers[x] == nn: self.pc += 2

            case 4: # skip if register x dne nn
                if self.registers[x] != nn: self.pc += 2

            case 5: # skip if register x equals y
                if n != 0:
                    panic()
                    return
                if self.registers[x] == self.registers[y]: self.pc += 2

            case 9: # skip if register x dne y
                if n != 0:
                    panic()
                    return
                if self.registers[x] != self.registers[y]: self.pc += 2

            case 6: # set register x to nn
                self.registers[x] = nn

            case 7: # add nn to register x
                self.registers[x] = (self.registers[x] + nn) % 256

            case 8: # arithmetic instructions
                match n:
                    case 0: self.registers[x] = self.registers[y]
                    case 1: self.registers[x] |= self.registers[y]
                    case 2: self.registers[x] &= self.registers[y]
                    case 3: self.registers[x] ^= self.registers[y]
                    case 4:
                        self.registers[x] += self.registers[y]
                        self.registers[-1] = 1 if self.registers[x] > 255 else 0
                        self.registers[x] %= 256
                    case 5:
                        self.registers[-1] = 1 if self.registers[x] >= self.registers[y] else 0
                        self.registers[x] = (self.registers[x] - self.registers[y]) % 256
                    case 7:
                        self.registers[-1] = 1 if self.registers[y] >= self.registers[x] else 0
                        self.registers[x] = (self.registers[y] - self.registers[x]) % 256
                    case 6:
                        if SET_SHIFT: self.registers[x] = self.registers[y]
                        self.registers[-1] = self.registers[x] & 0x1
                        self.registers[x] >>= 1
                    case 0xE:
                        if SET_SHIFT: self.registers[x] = self.registers[y]
                        self.registers[-1] = self.registers[x] >> 7
                        self.registers[x] = (self.registers[x] << 1) % 256
                    case _:
                        panic()

            case 0xA: # set the index register to nnn
                self.i_register = nnn

            case 0xB: # jump with offset
                self.pc = nnn + self.registers[x if JUMP_WITH_OFFSET_VX else 0]

            case 0xC: # random
                rand_num = random.randint(0, 255)
                self.registers[x] = rand_num & nn

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

            case 0xE:
                if nn == 0x9E: # skip if key currently pressed
                    target_key = KEYCODES[self.registers[x]]
                    if pygame.key.get_pressed()[target_key]:
                        self.pc += 2
                elif nn == 0xA1:
                    target_key = KEYCODES[self.registers[x]]
                    if not pygame.key.get_pressed()[target_key]:
                        self.pc += 2
                else:
                    panic()

            case 0xF:
                match nn:
                    case 0x07:
                        self.registers[x] = self.delay_timer
                    case 0x15:
                        self.delay_timer = self.registers[x]
                    case 0x18:
                        self.sound_timer = self.registers[x]
                    case 0x1E:
                        self.i_register += self.registers[x]
                    case 0x0A:
                        target_key = KEYCODES[self.registers[x]]
                        if not pygame.key.get_pressed()[target_key]:
                            self.pc -= 2
                    case 0x29:
                        self.i_register = FONT_DATA_POINTER + self.registers[x]
                    case 0x33:
                        val = self.registers[x]
                        for i in range(3):
                            self.memory[self.i_register + (2 - i)] = val % 10
                            val //= 10
                    case 0x55:
                        for i in range(x + 1):
                            self.memory[self.i_register + i] = self.registers[i]
                    case 0x65:
                        for i in range(x + 1):
                            self.registers[i] = self.memory[self.i_register + i]
                    case _:
                        panic()

            case _:
                panic()

class Chip8:
    def __init__(self, rom_path):
        rom_bytes = []
        with open(rom_path, 'rb') as rom:
            while (byte := rom.read(1)):
                rom_bytes.append(int.from_bytes(byte))

        processor = Processor()
        processor.load_rom(rom_bytes)

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
            processor.tick_timers()

            for _ in range(INSTRUCTIONS_PER_FRAME):
                processor.execute(processor.fetch())

            # 3: display screen_data
            self.draw_screen(processor.screen_data)
            pygame.display.update()

    def draw_screen(self, screen_data):
        for col in range(DISPLAY_SIZE[0]):
            for row in range(DISPLAY_SIZE[1]):
                color = COLOR_1 if screen_data[row][col] else COLOR_0
                x = col * DISPLAY_PIXEL_WIDTH
                y = row * DISPLAY_PIXEL_WIDTH
                pygame.draw.rect(self.screen, color, [x, y, x + DISPLAY_PIXEL_WIDTH, y + DISPLAY_PIXEL_WIDTH])


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Error: must specify a ROM to load")
        sys.exit(1)
    
    test = Chip8(sys.argv[1])