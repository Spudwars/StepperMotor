#! /usr/bin/python
import os
import time

from parallel import Parallel

'''
motor_position.py
=================

- Requirements:
$ pip install parallel, mock

- Assumes that at first, motor is in state 0 and will move to first index (0x07)

- There may be a slight loss in accuracy converting state to offset for
  calculating cycles


TODO
====

Test all argparse usages

argparse options checking



 
'''

# configure this per motor to be all the values to rotate a motor 360 degrees
MOTOR_INPUTS = [0x05, 0x07, 0x06, 0x0E, 0x0A, 0x0B, 0x09, 0x0D] * 3

def state_to_offset(state):
    '''
    Converts state (index into motor input positions) into an offset from 0 - 1
    
    :param state: Motor position state as index
    :type state: int
    :returns: Offset from 0 to 1
    :rtype: float
    '''
    # if 24 positions, position 23 is the last index, but is not quite 360deg
    # rotated (has 1 more step until one whole cycle offset)
    return float(state) / len(MOTOR_INPUTS)


def offset_to_state(offset):
    '''
    Converts offset as above to state (index into motor input positions)
    
    :param state: Offset from 0 to 1
    :type state: float
    :returns: Motor position state as index
    :rtype: int
    '''
    assert 0 <= offset <= 1
    return len(MOTOR_INPUTS) * float(offset)


def angle_to_cycles(angle, current_state):
    '''
    '''
    current_offset = state_to_offset(current_state)
    cycles = (angle / 360.0) - current_offset
    return cycles


def state_to_angle(state):
    '''
    '''
    #Q: state 48 should return 720 or 0?
    return 360.0 / len(MOTOR_INPUTS) * state


def stepper_generator(current_state, state_steps):
    '''
    Returns a generator object which yields the current state and motor input.
    
    :param current_state: Current index into the motor state list.
    :type current_state: int
    :param state_steps: Number of steps to step the motor.
    :type state_steps: int
    :returns: Generator yielding tuples (state_index, motor_input)
    :rtype: (int, hex)
    '''
    if state_steps < 0:
        step = -1
    else:
        step = 1
    
    state_index = current_state
    for virtual_state in xrange(current_state+1, current_state+state_steps+1, step):
        # NOTE: virtual_state is not used other than for informing the user the 
        # overall relative step we've applied!  
        state_index += step
        if state_index > len(MOTOR_INPUTS):
            # start at list 0
            state_index = 0
        elif state_index < len(MOTOR_INPUTS):
            # start at the end
            state_index = len(MOTOR_INPUTS)
        else:
            # we're at an index within the current motor inputs list
            pass
        
        print "%03d : Moving to state index %02d, %s hex %03.2f degrees" % (
            virtual_state, state_index, hex(MOTOR_INPUTS[state_index]),
            state_to_angle(state_index))

        # present the required value
        yield state_index, MOTOR_INPUTS[state_index]


def turn_motor(cycles, current_state, delay=0.05):
    '''
    Turns the motor the desired amount.
    
    :param cycles: Loops to turn
    :type cycles: float
    :param current_state: Current motor position
    :type current_state: int
    :param delay: Delay between steps (speed)
    :type delay: float
    :returns: New state position
    :rtype: int
    '''
    # round to the nearest step possible
    steps = round(cycles * len(MOTOR_INPUTS))
    
    p = Parallel()
    stepper = stepper_generator(current_state, steps)
    
    for new_state, motor_position in stepper:
        print "turn motor to position %s" % motor_position
        p.setData(motor_position)
        time.sleep(delay)

    return new_state
            

if __name__ == '__main__':
    import argparse
    example = """
Turn motor 1.3 turns anti clockwise, slowly:
$ motor_position.py --cycle -1.3 --delay 0.5

Turn motor 180 degrees (half a turn) clockwise from its current position:
$ motor_position.py --rotate 180

Turn motor to 0 degrees absolute angle
$ motor_position.py --angle 0
"""
    parser = argparse.ArgumentParser(description="Control a motor position.%s" % example)
    parser.add_argument('-c', '--cycle', type=float, default=None, 
                        help='Number of clockwise loops to cycle the motor. Negative cycles turn the motor counter clockwise!')
    parser.add_argument('-r', '--rotate', type=float, default=None, 
                        help='Angle to rotate motor clockwise to. Negative rotate turns the motor counter clockwise!')
    parser.add_argument('-a', '--angle', type=float, default=None, 
                        help='Absolute angle to rotate motor to. Range 0-360 degrees.')
    parser.add_argument('-d', '--delay', type=float, default=0.05,
                        help='Delay between stepper positions. Controls speed of motor!')
    parser.add_argument('-l', '--list', action='store_true',
                        default=False, help='List motor hex positions.')
    parser.add_argument('--state_file', type=str, default='motor_state.ini',
                        help='Path of file to store motor position state.')                 
    parser.add_argument('--reset', action='store_true', default=False,
                        help = 'Reset stored state to 0 degrees.')
    args = parser.parse_args()
    
    # todo: check arguments are valid, this is only a start - can't allow ANGLE too!
    if args.cycle and args.rotate:
        parser.error('Cannot cycle and rotate, please provide only one!')


    if args.list:
        print "Motor positions:"
        for n, p in enumerate(MOTOR_INPUTS):
            print "%d : %03.2f deg : %s hex" % (n, state_to_angle(n), hex(p))
        parser.exit()
    
    # if reset, do this first
    if args.reset:
        if os.path.isfile(args.state_file):
            os.remove(args.state_file)
        else:
            print "File not found: %s" % os.path.abspath(args.state_file)

    if os.path.isfile(args.state_file):
        # read in state position
        with open(args.state_file, 'r') as fh:
            # currently storing this value only!
            state = int(fh.read())
    else:
        print "Creating new state file"
        state = 0
        with open(args.state_file, 'w') as fh:
            fh.write(str(state))

    # calculate number of cycles to turn
    if args.cycle:
        cycles = args.cycle
    elif args.rotate:
        cycles = args.rotate / 360.0
    elif args.angle:
        cycles = angle_to_cycles(args.angle, state)
    else:
        parser.error("You must provide cycle or rotate to work")
    
    new_state = turn_motor(cycles, state, args.delay)

    # save state to file
    with open(args.state_file, 'w') as fh:
        fh.write(str(new_state))
