import RPi.GPIO as GPIO
import curses

# Configura el modo de numeración de pines a BOARD
GPIO.setmode(GPIO.BOARD)

# Define los pines PWM
pin_pwm0 = 32
pin_pwm1 = 33

# Configura los pines como salidas
GPIO.setup(pin_pwm0, GPIO.OUT)
GPIO.setup(pin_pwm1, GPIO.OUT)

# Configura los pines para PWM con una frecuencia de 100Hz
pwm0 = GPIO.PWM(pin_pwm0, 100)
pwm1 = GPIO.PWM(pin_pwm1, 100)

# Inicializa variables para el control de duty cycle y estado de PWM
duty_cycle = 50
active_pwm0 = False
active_pwm1 = False

def toggle_single_pwm(pwm_to_toggle, other_pwm):
    global active_pwm0, active_pwm1
    if pwm_to_toggle == pwm0:
        active_pwm0 = not active_pwm0
        active_pwm1 = False
    else:
        active_pwm1 = not active_pwm1
        active_pwm0 = False

    if active_pwm0:
        pwm0.start(duty_cycle)
        pwm1.stop()
    elif active_pwm1:
        pwm1.start(duty_cycle)
        pwm0.stop()
    else:
        pwm0.stop()
        pwm1.stop()

def adjust_duty(adjustment):
    global duty_cycle
    new_duty = duty_cycle + adjustment
    duty_cycle = max(0, min(100, new_duty))
    if active_pwm0:
        pwm0.ChangeDutyCycle(duty_cycle)
    if active_pwm1:
        pwm1.ChangeDutyCycle(duty_cycle)

def main(stdscr):

    stdscr.nodelay(True)
    stdscr.timeout(1000)

    try:
        while True:
            c = stdscr.getch()
            if c == ord('q'):
                toggle_single_pwm(pwm0, pwm1)
            elif c == ord('w'):
                toggle_single_pwm(pwm1, pwm0)
            elif c == ord('a'):
                adjust_duty(10)
            elif c == ord('z'):
                adjust_duty(-10)
            elif c == ord('x'):
                break

    except KeyboardInterrupt:
        pass

    finally:
        pwm0.stop()
        pwm1.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    curses.wrapper(main)

