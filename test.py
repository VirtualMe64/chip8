import unittest
from unittest.mock import patch
from chip8 import Processor

def split_instructions(program):
    out = []
    for inst in program:
        out.append(inst >> 8)
        out.append(inst & 0xFF)
    return out

def setup_registers(registers):
    def hook(processor):
        for x, y in registers.items():
            processor.registers[x] = y
    return hook

class Chip8Test(unittest.TestCase):
    def program_test(
            self, 
            program, 
            expected_register_values = None,
            expected_pc = None,
            expected_i_reg = None,
            stack_test = None,
            screen_test = None, 
            setup_hook = None, 
            max_steps = 1000
    ):
        # executes program and checks if output matches expectation
        processor = Processor()
        processor.load_rom(split_instructions(program))
        
        if setup_hook is not None:
            setup_hook(processor)

        i = 0
        while 512 <= processor.pc <= 512 + ((len(program) - 1) * 2) and i < max_steps:
            processor.execute(processor.fetch())
            if i % 10 == 0:
                processor.tick_timers()
            i += 1

        if expected_register_values is not None:
            for reg, val in expected_register_values.items():
                self.assertEqual(processor.registers[reg], val)

        if expected_pc is not None:
            self.assertEqual(processor.pc, expected_pc)

        if expected_i_reg is not None:
            self.assertEqual(processor.i_register, expected_i_reg)

        if stack_test is not None:
            stack_test(processor.stack)

        if screen_test is not None:
            screen_test(processor.screen_data)

        self.assertEqual(1, 1)

class TestClearScreen(Chip8Test):
    def test_clears(self):
        program = [0x00E0]

        def screen_setup(processor : Processor):
            processor.screen_data[0][0] = True

        def screen_test(screen_data):
            self.assertFalse(any(any(row) for row in screen_data))

        self.program_test(program, setup_hook = screen_setup, screen_test=screen_test)

class TestJump(Chip8Test):
    def test_jumps(self):
        program = [0x1123] # jump to 1
        self.program_test(program, expected_pc=0x123)

class TestSubroutines(Chip8Test):
    def test_jumps(self):
        # call a subroutine which jumps to 2
        program = [0x2204, 0x1001, 0x1002]
        self.program_test(program, expected_pc=2)

    def test_returns(self):
        # call a subroutine which immediately returns, then jump to 1
        program = [0x2204, 0x1001, 0x00EE, 0x1002]
        self.program_test(program, expected_pc=1)

    def test_stack_pop(self):
        program = [0x2204, 0x1001, 0x00EE, 0x1002]
        self.program_test(program, stack_test=lambda stack : self.assertEqual(len(stack), 0))
    
    def test_stack_push(self):
        # calls a subroutine which exits
        program = [0x2202, 0x1001]
        def stack_test(stack):
            self.assertEqual(len(stack), 1)
            self.assertEqual(stack[0], 0x202)
        self.program_test(program, stack_test=stack_test)

class TestConditionalSkips(Chip8Test):
    def test_3x_skips(self):
        program = [0x3142] # skip if register 1 = 0x42
        self.program_test(program, setup_hook=setup_registers({1: 0x42}), expected_pc=0x204)
    
    def test_3x_doesnt_skip(self):
        program = [0x3142] # skip if register 1 = 0x42
        self.program_test(program, setup_hook=setup_registers({1: 0x43}), expected_pc=0x202)

    def test_4x_skips(self):
        program = [0x4142] # skip if register 1 != 0x42
        self.program_test(program, setup_hook=setup_registers({1: 0x43}), expected_pc=0x204)
    
    def test_4x_doesnt_skip(self):
        program = [0x4142] # skip if register 1 != 0x42
        self.program_test(program, setup_hook=setup_registers({1: 0x42}), expected_pc=0x202)

    def test_5x_skips(self):
        program = [0x5120] # skip if register 1 == register 2
        self.program_test(program, setup_hook=setup_registers({1: 0x42, 2: 0x42}), expected_pc=0x204)
    
    def test_5x_doesnt_skip(self):
        program = [0x5120] # skip if register 1 == register 2
        self.program_test(program, setup_hook=setup_registers({1: 0x42, 2: 0x43}), expected_pc=0x202)

    def test_9x_skips(self):
        program = [0x9120] # skip if register 1 != register 2
        self.program_test(program, setup_hook=setup_registers({1: 0x42, 2: 0x43}), expected_pc=0x204)
    
    def test_9x_doesnt_skip(self):
        program = [0x9120] # skip if register 1 != register 2
        self.program_test(program, setup_hook=setup_registers({1: 0x42, 2: 0x42}), expected_pc=0x202)

class TestSet(Chip8Test):
    def test_set(self):
        program = [0x6142] # set register 1 to 0x42
        self.program_test(program, expected_register_values={1: 0x42})

class TestAdd(Chip8Test):
    def test_no_overflow(self):
        program = [0x6140, 0x7102] # set register 1 to 0x40 then add 0x2
        self.program_test(program, expected_register_values={1: 0x42, 0xF: 0x0})
    
    def test_overflow(self):
        program = [0x61FE, 0x7103] # set register 1 to 0xFE then add 0x3. Should overflow to 1
        self.program_test(program, expected_register_values={1: 0x1, 0xF: 0x0})

class TestArithmetic(Chip8Test):
    def test_set(self):
        program = [0x8120] # set reg 1 to reg 2
        self.program_test(program,
            setup_hook=setup_registers({1: 0x0, 2: 0x42}),
            expected_register_values={1: 0x42, 2: 0x42, 0xF: 0}
        )
    
    def test_or(self):
        program = [0x8121] # or reg 1 with reg 2
        self.program_test(program,
            setup_hook=setup_registers({1: 0x1, 2: 0x2}),
            expected_register_values={1: 0x3, 2: 0x2, 0xF: 0}
        )
    
    def test_and(self):
        program = [0x8122] # and reg 1 with reg 2
        self.program_test(program,
            setup_hook=setup_registers({1: 0x6, 2: 0x3}),
            expected_register_values={1: 0x2, 2: 0x3, 0xF: 0}
        )
    
    def test_xor(self):
        program = [0x8123] # xor reg 1 with reg 2
        self.program_test(program,
            setup_hook=setup_registers({1: 0x6, 2: 0x3}),
            expected_register_values={1: 0x5, 2: 0x3, 0xF: 0}
        )

    def test_add_no_carry(self):
        program = [0x8124] # add reg 2 to reg 1
        self.program_test(program,
            setup_hook=setup_registers({1: 0x40, 2: 0x2}),
            expected_register_values={1: 0x42, 2: 0x2, 0xF: 0}
        )

    def test_add_carry(self):
        program = [0x8124] # add reg 2 to reg 1
        self.program_test(program,
            setup_hook=setup_registers({1: 0xFE, 2: 0x3}),
            expected_register_values={1: 0x1, 2: 0x3, 0xF: 1}
        )

    def test_sub1_no_carry(self):
        program = [0x8125] # reg1 = reg1 - reg2
        self.program_test(program,
            setup_hook=setup_registers({1: 0x9, 2: 0x5}),
            expected_register_values={1: 0x4, 2: 0x5, 0xF: 1}
        )
    
    def test_sub1_carry(self):
        program = [0x8125] # reg1 = reg1 - reg2
        self.program_test(program,
            setup_hook=setup_registers({1: 0x1, 2: 0x3}),
            expected_register_values={1: 0xFE, 2: 0x3, 0xF: 0}
        )
    
    def test_sub2_no_carry(self):
        program = [0x8127] # reg1 = reg2 - reg1
        self.program_test(program,
            setup_hook=setup_registers({1: 0x5, 2: 0x9}),
            expected_register_values={1: 0x4, 2: 0x9, 0xF: 1}
        )
    
    def test_sub2_carry(self):
        program = [0x8127] # reg1 = reg2 - reg1
        self.program_test(program,
            setup_hook=setup_registers({1: 0x3, 2: 0x1}),
            expected_register_values={1: 0xFE, 2: 0x1, 0xF: 0}
        )

    def test_shift_right(self):
        program = [0x8116] # reg1 = reg1 >> 1
        self.program_test(program,
            setup_hook=setup_registers({1: 15}),
            expected_register_values={1: 7, 0xF: 1}
        )
        self.program_test(program,
            setup_hook=setup_registers({1: 14}),
            expected_register_values={1: 7, 0xF: 0}
        )
    
    def test_shift_left(self):
        program = [0x811E] # reg1 = reg1 << 1
        self.program_test(program,
            setup_hook=setup_registers({1: 0xFF}),
            expected_register_values={1: 0xFE, 0xF: 1}
        )
        self.program_test(program,
            setup_hook=setup_registers({1: 0x7F}),
            expected_register_values={1: 0xFE, 0xF: 0}
        )

class TestSetIndex(Chip8Test):
    def test_set_index(self):
        program = [0xA123] # set i_reg to 0x123
        self.program_test(program, expected_i_reg=0x123)

class TestJumpWithOffset(Chip8Test):
    def test_jump_with_offset(self):
        program = [0xB200] # jump to 0x200 + v0
        self.program_test(program,
            setup_hook=setup_registers({0: 0x8}),
            expected_pc=0x208
        )

class TestRandom(Chip8Test):
    @patch('random.randint', return_value=0x42)
    def test_random_ands(self, mock_randint):
        program = [0xC100] # set reg 1 to rand & 00
        self.program_test(program,
            setup_hook=setup_registers({1: 0x1}),
            expected_register_values={1: 0x0}
        )

    @patch('random.randint', return_value=0x42)
    def test_random_value(self, mock_randint):
        program = [0xC1FF] # set reg 1 to rand & 00
        self.program_test(program, expected_register_values={1: 0x42})

class TestDisplay(Chip8Test):
    def test_basic_draw(self):
        program = [0xA000, 0xD122] # draw a two row high sprite (at mem 0) at x = register 1, y = register 2
        
        def setup(processor : Processor):
            processor.registers[1] = 1
            processor.registers[2] = 1
            processor.memory[0] = 0xFF
            processor.memory[1] = 0x81

        def screen_test(screen):
            expected_screen = [
                [False if c == '0' else True for c in '0000000000'],
                [False if c == '0' else True for c in '0111111110'],
                [False if c == '0' else True for c in '0100000010'],
                [False if c == '0' else True for c in '0000000000'],
            ]
            for y in range(len(expected_screen)):
                for x in range(len(expected_screen[0])):
                    self.assertEqual(screen[y][x], expected_screen[y][x])

        self.program_test(
            program,
            screen_test=screen_test,
            setup_hook=setup
        )
    
    def test_draw_1_row(self):
        program = [0xA000, 0xD121] # draw a one row high sprite (at mem 0) at x = register 1, y = register 2
        
        def setup(processor : Processor):
            processor.registers[1] = 1
            processor.registers[2] = 1
            processor.memory[0] = 0xFF
            processor.memory[1] = 0x81

        def screen_test(screen):
            expected_screen = [
                [False if c == '0' else True for c in '0000000000'],
                [False if c == '0' else True for c in '0111111110'],
                [False if c == '0' else True for c in '0000000000'],
                [False if c == '0' else True for c in '0000000000'],
            ]
            for y in range(len(expected_screen)):
                for x in range(len(expected_screen[0])):
                    self.assertEqual(screen[y][x], expected_screen[y][x])

        self.program_test(
            program,
            screen_test=screen_test,
            setup_hook=setup
        )

    def test_draw_modulo(self):
        program = [0xA000, 0xD122] # draw a two row high sprite (at mem 0) at x = register 1, y = register 2
        
        def setup(processor : Processor):
            processor.registers[1] = 65
            processor.registers[2] = 33
            processor.memory[0] = 0xFF
            processor.memory[1] = 0x81

        def screen_test(screen):
            expected_screen = [
                [False if c == '0' else True for c in '0000000000'],
                [False if c == '0' else True for c in '0111111110'],
                [False if c == '0' else True for c in '0100000010'],
                [False if c == '0' else True for c in '0000000000'],
            ]
            for y in range(len(expected_screen)):
                for x in range(len(expected_screen[0])):
                    self.assertEqual(screen[y][x], expected_screen[y][x])

        self.program_test(
            program,
            screen_test=screen_test,
            setup_hook=setup
        )
    
    def test_draw_cutoff(self):
        program = [0xA000, 0xD122] # draw a two row high sprite (at mem 0) at x = register 1, y = register 2
        
        def setup(processor : Processor):
            processor.registers[1] = 62
            processor.registers[2] = 30
            processor.memory[0] = 0xFF
            processor.memory[1] = 0x81

        def screen_test(screen):
            screen_segment = [row[-3:] for row in screen[-3:]]
            expected_screen = [
                [False if c == '0' else True for c in '000'],
                [False if c == '0' else True for c in '011'],
                [False if c == '0' else True for c in '010']
            ]
            for y in range(len(expected_screen)):
                for x in range(len(expected_screen[0])):
                    self.assertEqual(screen_segment[y][x], expected_screen[y][x])

        self.program_test(
            program,
            screen_test=screen_test,
            setup_hook=setup
        )