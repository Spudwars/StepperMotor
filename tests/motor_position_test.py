import mock
import unittest

from motor_position import (angle_to_cycles,
                            offset_to_state,
                            state_to_offset,
                            stepper_generator,
                            turn_motor,
                            )

class TestMotorPosition(unittest.TestCase):
    
    def test_state_offset_conversions(self):
        self.assertEqual(state_to_offset(0), 0)
        self.assertEqual(state_to_offset(24), 1)
        self.assertEqual(state_to_offset(12), 0.5)
        self.assertAlmostEqual(state_to_offset(23), 0.95)
                
        self.assertEqual(offset_to_state(0), 0)
        self.assertEqual(offset_to_state(1), 24)
        self.assertRaises(AssertionError, offset_to_state, 1.1)
        self.assertRaises(AssertionError, offset_to_state, -12)
        
        # both ways convert back to the original
        self.assertEqual(state_to_offset(offset_to_state(0.5)), 0.5)    
    
    def test_state_to_angle(self):
        self.assertEqual(state_to_angle(0), 0)
        self.assertEqual(state_to_angle(12), 180)
        self.assertEqual(state_to_angle(24), 360) #Q: Should this return 0 or 360????       
    
    def test_angle_to_cycles(self):
        self.assertEqual(angle_to_cycles(0, 0), 0)
        self.assertEqual(angle_to_cycles(360, 0), 0)
        self.assertEqual(angle_to_cycles(720, 0), 0)
        
        self.assertEqual(angle_to_cycles(180, 12), 0)
        self.assertEqual(angle_to_cycles(180, 0), 0.5)
        
        # forwards quarter a turn
        self.assertEqual(angle_to_cycles(270, 12), 0.25)
        # backwards quarter a turn
        self.assertEqual(angle_to_cycles(180, 16), -0.25)
        
    def test_stepper_generator_forward(self):
        gen1 = stepper_generator(0, 4)
        self.assertEqual(gen1.next(), (1, 0x07))
        self.assertEqual(gen1.next(), (2, 0x06))
        self.assertEqual(gen1.next(), (3, 0x0E))
        self.assertEqual(gen1.next(), (4, 0x0A))
        # generator has now expired
        self.assertRaises(StopIteration, gen1.next)
        
        # test going over the end
        gen1 = stepper_generator(22, 10)
        self.assertEqual(gen1.next(), (22, 0x09))
        self.assertEqual(gen1.next(), (23, 0x0D))
        self.assertEqual(gen1.next(), (1, 0x05))
        self.assertEqual(gen1.next(), (2, 0x07))
        
    def test_stepper_generator_reverse(self):
        gen1 = stepper_generator(3, -6)
        self.assertEqual(gen1.next(), (2, 0x06))
        self.assertEqual(gen1.next(), (1, 0x07))
        self.assertEqual(gen1.next(), (0, 0x05))
        self.assertEqual(gen1.next(), (23, 0x0D)) # end of 24 positions
        self.assertEqual(gen1.next(), (22, 0x09))
        self.assertEqual(gen1.next(), (21, 0x0B))
        
        # generator has now expired
        self.assertRaises(StopIteration, gen1.next)
        
    def test_turn_motor(self):
        # monkey patch Parallel with mock
        import motor_position
        mock_parallel = mock.Mock()
        motor_position.Parallel = mock_parallel
        
        # turn 1 x rotation == 24 x steps
        new_state = turn_motor(1, 2)
        # returned to state 2 (starting point)
        self.assertEqual(new_state, 2)
        # called parallel 24 times for full cycle
        self.assertEqual(mock_parallel.setData.call_count, 24)
        # test the last few commands were forwards
        self.assertEqual(mock_parallel.setData.call_args[-4:],
                         (0x0D, 0X05, 0X07, 0x06))

        
    def test_turn_motor_backwards(self):
        # monkey patch Parallel with mock
        import motor_position
        mock_parallel = mock.Mock()
        motor_position.Parallel = mock_parallel

        # turn -2.5 x rotation == 52 x steps
        new_state = turn_motor(-2.5, 0)
        self.assertEqual(new_state, 12)
        self.assertEqual(mock_parallel.setData.call_count, 52)
        # check last few steps were correct, going backwards to half a turn
        self.assertEqual(mock_parallel.setData.call_args[-3:],
                         (0X09, 0X0B, 0x0A))
        
        
    def test_turn_motor_nowhere(self):
        "Ensure that 0 cycles doens't break!"
        import motor_position
        mock_parallel = mock.Mock()
        motor_position.Parallel = mock_parallel
        
        # turn 0 x rotation == 0 x steps
        new_state = turn_motor(0, 11)
        # stayed at offset 11
        self.assertEqual(new_state, 11)
        self.assertEqual(mock_parallel.setData.call_count, 0)
        self.assertEqual(mock_parallel.setData.call_args, ())
        