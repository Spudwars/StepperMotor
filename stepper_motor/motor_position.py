#! /usr/bin/python
import os
import time

try:
    from parallel import Parallel
except ImportError:
    print "Requires Java Communications API and pyparallel"
    print "http://sourceforge.net/projects/pyserial/files/pyparallel/0.2/"
    #raise
    
    print "WARNING: Running in Dry Run mode without parallel port control!"
    class Printer(object):
        call_count = 0
        def setData(self, x):
            self.call_count += 1
            #print "< would like to send '%s' to parallel port! >" % hex(x)
    Parallel = Printer

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
    
    :param offset: Offset from 0 to 1
    :type offset: float
    :returns: Motor position state as index
    :rtype: int
    '''
    assert 0 <= offset <= 1
    return len(MOTOR_INPUTS) * float(offset)


def angle_to_cycles(angle, current_state):
    '''
    Converts an absolute angle to the offset required to turn the motor from
    the current state.
    
    Note: will find the shortest rotation, clockwise or anti-clockwise.
    
    TODO: allow override to force direction if required.
    
    :param angle: Desired angle
    :type angle: float
    :param current_state: Motor position state as index
    :type current_state: int
    :returns: Cycles to rotate motor
    :rtype: float between -1 and 1
    '''
    current_offset = state_to_offset(current_state)
    desired_offset = (angle%360 / 360.0)
    #Q: Is there an easier way to find the minimum distance?
    fwd_cycles = desired_offset - current_offset
    rev_cycles = desired_offset - current_offset - 1
    zero_first = lambda a, b: cmp(abs(a), abs(b))
    return sorted((fwd_cycles, rev_cycles), zero_first)[0]


def state_to_angle(state):
    '''
    Converts a state to angle.
    
    :param state: Motor position state as index
    :type state: int
    :returns: Angle
    :rtype: float
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
        if state_index >= len(MOTOR_INPUTS):
            # start at list 0
            state_index = 0
        elif state_index < 0:
            # start at the end
            state_index = len(MOTOR_INPUTS) -1
        else:
            # we're at an index within the current motor inputs list
            pass
        
        print "%+ 4d : Moving to internal state index %02d, %s hex %03.2f degrees" % (
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
    steps = int(round(cycles * len(MOTOR_INPUTS)))
    
    p = Parallel()
    stepper = stepper_generator(current_state, steps)
    
    for current_state, motor_position in stepper:
        ##print "turn motor to position %s" % hex(motor_position)
        p.setData(motor_position)
        time.sleep(delay)

    return current_state
            

if __name__ == '__main__':
    import argparse
    example = """

Here follow some examples:

Turn motor 1.3 turns anti clockwise, slowly from 0:
$ motor_position.py --cycle -1.3 --delay 0.5 --reset

   +1 : Moving to internal state index 23, 0xd hex 345.00 degrees
   +0 : Moving to internal state index 22, 0x9 hex 330.00 degrees
   -1 : Moving to internal state index 21, 0xb hex 315.00 degrees
   -2 : Moving to internal state index 20, 0xa hex 300.00 degrees
   -3 : Moving to internal state index 19, 0xe hex 285.00 degrees
 ...
  -28 : Moving to internal state index 18, 0x6 hex 270.00 degrees
  -29 : Moving to internal state index 17, 0x7 hex 255.00 degrees
 Saved new state index 17 to file: motor_state.ini


Turn motor 45 degrees (eighth a turn) clockwise from its current position:
$ motor_position.py --rotate 45

 Read in current state position as 17
  +18 : Moving to internal state index 18, 0x6 hex 270.00 degrees
  +19 : Moving to internal state index 19, 0xe hex 285.00 degrees
  +20 : Moving to internal state index 20, 0xa hex 300.00 degrees
 Saved new state index 20 to file: motor_state.ini


Turn motor to 270 degrees absolute angle, from the current 300 degrees angle.
$ motor_position.py --angle 270

 Read in current state position as 20
  +21 : Moving to internal state index 19, 0xe hex 285.00 degrees
  +20 : Moving to internal state index 18, 0x6 hex 270.00 degrees
 Saved new state index 18 to file: motor_state.ini
"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Control a motor position.%s" % example)
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
                        help='Reset stored state to 0 degrees before processing request.')
    args = parser.parse_args()
    
    # todo: check arguments are valid, this is only a start - can't allow ANGLE too!
    if (args.cycle and args.rotate) \
       or (args.rotate and args.angle) \
       or (args.angle and args.rotate):
        parser.error('Cannot combine cycle, rotate and angle, please provide only one!')


    if args.list:
        print "Motor positions:"
        for n, p in enumerate(MOTOR_INPUTS):
            print "%d : %03.2f deg : %s hex" % (n, state_to_angle(n), hex(p))
        parser.exit()
    
    # if reset, do this first
    if args.reset:
        if os.path.isfile(args.state_file):
            print "Reseting state by deleting state file"
            os.remove(args.state_file)
        else:
            print "File not found: %s" % os.path.abspath(args.state_file)

    if os.path.isfile(args.state_file):
        # read in state position
        with open(args.state_file, 'r') as fh:
            # currently storing this value only!
            state = int(fh.read())
            print "Read in current state position as %02d" % state
    else:
        print "Creating initial state file, assuming current state is 00"
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
    elif args.reset:
        # only reset required, exit
        parser.exit()
    else:
        parser.error("You must provide cycle or rotate to work")
    
    new_state = turn_motor(cycles, state, args.delay)

    # save state to file
    with open(args.state_file, 'w') as fh:
        fh.write(str(new_state))
        print "Saved new state index %02d to file: %s" % (
            new_state, args.state_file)

    print "FINISHED"