import mock
import unittest

from stepper_motor.motor_position import (
    angle_to_cycles,
    offset_to_state,
    state_to_angle,
    state_to_offset,
    StepperMotor,
)

class TestMotorPosition(unittest.TestCase):
    
    def setUp(self):
        # overide the motor inputs to a more manageable number
        self.MOTOR_INPUTS = [0x05, 0x07, 0x06, 0x0E, 0x0A, 0x0B, 0x09, 0x0D] * 3
    
    def test_state_offset_conversions(self):
        qty = 24
        self.assertEqual(state_to_offset(0, qty), 0)
        self.assertEqual(state_to_offset(24, qty), 1)
        self.assertEqual(state_to_offset(12, qty), 0.5)
        self.assertAlmostEqual(state_to_offset(23, qty), 0.96, 2)
        
        self.assertEqual(offset_to_state(0, qty), 0)
        self.assertEqual(offset_to_state(1, qty), 24)
        self.assertRaises(AssertionError, offset_to_state, 1.1, 24)
        self.assertRaises(AssertionError, offset_to_state, -12, 24)
        
        # both ways convert back to the original
        self.assertEqual(state_to_offset(offset_to_state(0.5, qty), qty), 0.5)    
    
    def test_state_to_angle(self):
        qty = 24
        self.assertEqual(state_to_angle(0, qty), 0)
        self.assertEqual(state_to_angle(12, qty), 180)
        self.assertEqual(state_to_angle(24, qty), 360) #Q: Should this return 0 or 360????       
    
    def test_angle_to_cycles(self):
        qty = 24 # states
        self.assertEqual(angle_to_cycles(0, 0, qty), 0)
        self.assertEqual(angle_to_cycles(360, 0, qty), 0)
        self.assertEqual(angle_to_cycles(720, 0, qty), 0)
        
        self.assertEqual(angle_to_cycles(180, 12, qty), 0)
        self.assertEqual(angle_to_cycles(180, 0, qty), 0.5)
        
        # forwards quarter a turn
        self.assertEqual(angle_to_cycles(270, 12, qty), 0.25)
        # backwards quarter a turn
        self.assertEqual(angle_to_cycles(180, 18, qty), -0.25)
        
    def test_angle_to_cycles_shortest_distance(self):
        qty = 24
        # quarter turn forwards
        self.assertEqual(angle_to_cycles(180, 6, qty), 0.25)
        # quarter turn backwards
        self.assertEqual(angle_to_cycles(180, 18, qty), -0.25)
        # quarter turn over rollover backwards
        self.assertEqual(angle_to_cycles(300, 2, qty), -0.25)
        
    def test_stepper_generator_forward(self):
        stepper = StepperMotor(self.MOTOR_INPUTS, state=0)
        gen1 = stepper.stepper_generator(4)
        self.assertEqual(gen1.next(), 0x07)
        self.assertEqual(stepper.state, 1)
        self.assertEqual(gen1.next(), 0x06)
        self.assertEqual(stepper.state, 2)
        self.assertEqual(gen1.next(), 0x0E)
        self.assertEqual(stepper.state, 3)
        self.assertEqual(gen1.next(), 0x0A)
        self.assertEqual(stepper.state, 4)
        # generator has now expired
        self.assertRaises(StopIteration, gen1.next)
        
    def test_stepper_generator_forward_rollover(self):
        # test going over the end
        stepper = StepperMotor(self.MOTOR_INPUTS, state=21)
        gen1 = stepper.stepper_generator(10)
        self.assertEqual(gen1.next(),  0x09)
        self.assertEqual(stepper.state, 22)
        self.assertEqual(gen1.next(),  0x0D)
        self.assertEqual(stepper.state, 23)
        self.assertEqual(gen1.next(), 0x05)
        self.assertEqual(stepper.state, 0)
        self.assertEqual(gen1.next(), 0x07)
        self.assertEqual(stepper.state, 1)
        
    def test_stepper_generator_reverse(self):
        stepper = StepperMotor(self.MOTOR_INPUTS, state=3)
        gen1 = stepper.stepper_generator(-6)
        self.assertEqual(gen1.next(), 0x06)
        self.assertEqual(stepper.state, 2)
        self.assertEqual(gen1.next(), 0x07)
        self.assertEqual(stepper.state, 1)
        self.assertEqual(gen1.next(), 0x05)
        self.assertEqual(stepper.state, 0)
        
        self.assertEqual(gen1.next(), 0x0D) # end of 24 positions
        self.assertEqual(stepper.state, 23)
        self.assertEqual(gen1.next(), 0x09)
        self.assertEqual(stepper.state, 22)
        self.assertEqual(gen1.next(), 0x0B)
        self.assertEqual(stepper.state, 21)
        
        # generator has now expired
        self.assertRaises(StopIteration, gen1.next)
        
    def test_turn_motor(self):
        mock_parallel = mock.Mock()
        stepper = StepperMotor(self.MOTOR_INPUTS, state=2)
        stepper.parallel_interface = mock_parallel
        
        # turn 1 x rotation == 24 x steps
        new_state = stepper.turn_motor(1)
        # returned to state 2 (starting point)
        self.assertEqual(new_state, 2)
        # called parallel 24 times for full cycle
        self.assertEqual(mock_parallel.setData.call_count, 24)
        # test the last few commands were forwards
        ##mock_parallel.setData.assert_has_calls(self.MOTOR_INPUTS[3:] + self.MOTOR_INPUTS[:3])
        self.assertEqual([c[0][0] for c in mock_parallel.setData.call_args_list[-4:]],
                         [0x0D, 0X05, 0X07, 0x06])
        
        
    def test_turn_motor_backwards(self):
        mock_parallel = mock.Mock()
        stepper = StepperMotor(self.MOTOR_INPUTS)
        stepper.parallel_interface = mock_parallel
        
        # turn -2.5 x rotation (24) == 60 x steps
        new_state = stepper.turn_motor(-2.5)
        self.assertEqual(new_state, 12)
        self.assertEqual(mock_parallel.setData.call_count, 60)
        # check last few steps were correct, going backwards to half a turn
        self.assertEqual([c[0][0] for c in mock_parallel.setData.call_args_list[-3:]],
                         [0X09, 0X0B, 0x0A])
        
        
    def test_turn_motor_nowhere(self):
        "Ensure that 0 cycles doens't break!"
        mock_parallel = mock.Mock()
        stepper = StepperMotor(self.MOTOR_INPUTS, state=11)
        stepper.parallel_interface = mock_parallel
        
        # turn 0 x rotation == 0 x steps
        new_state = stepper.turn_motor(0)
        # stayed at offset 11
        self.assertEqual(new_state, 11)
        self.assertEqual(mock_parallel.setData.call_count, 0)
        self.assertEqual(mock_parallel.setData.call_args, None)
        