StepperMotor
============

Python parallel interface to control a stepper motor.


```python
turn_motor(cycles, state, delay)
```


Sample Command Line Usage
-------------------------

Turn motor 1.3 turns anti clockwise, slowly from 0:

>$ motor_position.py --cycle -1.3 --delay 0.5 --reset

>  +1 : Moving to internal state index 23, 0xd hex 345.00 degrees
>  +0 : Moving to internal state index 22, 0x9 hex 330.00 degrees
>  -1 : Moving to internal state index 21, 0xb hex 315.00 degrees
>  -2 : Moving to internal state index 20, 0xa hex 300.00 degrees
>  -3 : Moving to internal state index 19, 0xe hex 285.00 degrees
>...
> -28 : Moving to internal state index 18, 0x6 hex 270.00 degrees
> -29 : Moving to internal state index 17, 0x7 hex 255.00 degrees
>Saved new state index 17 to file: motor_state.ini


Turn motor 45 degrees (eighth a turn) clockwise from its current position:

>$ motor_position.py --rotate 45

>Read in current state position as 17
> +18 : Moving to internal state index 18, 0x6 hex 270.00 degrees
> +19 : Moving to internal state index 19, 0xe hex 285.00 degrees
> +20 : Moving to internal state index 20, 0xa hex 300.00 degrees
>Saved new state index 20 to file: motor_state.ini


Turn motor to 270 degrees absolute angle, from the current 300 degrees angle.

>$ motor_position.py --angle 270

>Read in current state position as 20
> +21 : Moving to internal state index 19, 0xe hex 285.00 degrees
> +20 : Moving to internal state index 18, 0x6 hex 270.00 degrees
>Saved new state index 18 to file: motor_state.ini


Notes
-----

* Assumes that at first, motor is in state 0 and will move to first index (0x07)
* There may be a slight loss in accuracy converting state to offset for calculating cycles
* Assumes that 0 index is 0 degrees. Could have an offset but easier to calibrate device or change order of motor inputs.


