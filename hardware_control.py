import RPi.GPIO as GPIO

pin_pwm1 = 32
duty_cycle = 70

def init_pwm():
    try:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin_pwm1, GPIO.OUT)
        pwm1 = GPIO.PWM(pin_pwm1, 100)
        pwm1.start(duty_cycle)
        return pwm1
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def stop_pwm(pwm1):
    pwm1.stop()
    
