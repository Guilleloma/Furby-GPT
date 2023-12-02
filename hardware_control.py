import RPi.GPIO as GPIO
import time

pin_pwm1 = 32
pin_pwm2 = 33
pin_finalcarrera = 13
duty_cycle = 70

def init_pwm():
    try:
        GPIO.setmode(GPIO.BOARD)
        
        #PWM1
        GPIO.setup(pin_pwm1, GPIO.OUT)
        pwm1 = GPIO.PWM(pin_pwm1, 100)
        pwm1.start(duty_cycle)
        
        #PWM2
        GPIO.setup(pin_pwm2, GPIO.OUT)
        pwm2 = GPIO.PWM(pin_pwm2, 100)
        pwm2.start(duty_cycle)

        # Configura el pin con pull-up
        GPIO.setup(pin_finalcarrera , GPIO.IN, pull_up_down=GPIO.PUD_UP)

        return pwm1, pwm2
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

def stop_pwm(pwm1):
    pwm1.stop()

#Control de las posiciones del Motor

def run_motor_until_limitswitch(pwm1):
    while GPIO.input(pin_finalcarrera):
        pwm1.ChangeDutyCycle(duty_cycle)
    pwm1.ChangeDutyCycle(0)
    print("Final de carrera detectado.") 
    
def move_motor_for_seconds(pwm1, duration):
    pwm1.ChangeDutyCycle(duty_cycle)
    time.sleep(duration)
    pwm1.ChangeDutyCycle(0)   

## Secuencias de movimientos de motor
def motor_sequence_dormir(pwm1):
    run_motor_until_limitswitch(pwm1)
    move_motor_for_seconds(pwm1, 0.7)

    
def motor_sequence_pensando(pwm1,pwm2):
    #Ve al inicio del ciclo
    run_motor_until_limitswitch(pwm1)
    
    #Ve donde se mueven las orejas
    move_motor_for_seconds(pwm1, 1)
    #Muevela un poco hacia adelante
    move_motor_for_seconds(pwm1, 0.5)
    #Muevela un poco hacia atras
    move_motor_for_seconds(pwm2, 0.5)
