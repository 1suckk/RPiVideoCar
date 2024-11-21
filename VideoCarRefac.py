#creapple 사이트의 Rpi3b+ 기반의 코드를 Rpi4b의 Debian bookworm 64bits os로 refactoring해서 새로 만든 코드

from flask import Flask, render_template, request, Response
import RPi.GPIO as GPIO                 
import time      
import io
import threading
from picamera2 import Picamera2, Preview

class Camera:
    thread = None  
    frame = None  
    start_time = 0  

    def getStreaming(self):
        Camera.start_time = time.time()
        
        if Camera.thread is None:
            Camera.thread = threading.Thread(target=self.streaming)
            Camera.thread.start()

            while self.frame is None:
                time.sleep(0)
        return self.frame

    @classmethod
    def streaming(c):
        picam2 = Picamera2()

        # 카메라 화면 180도 회전
        transform = Transform(hflip=True, vflip=True)
        
        config = picam2.create_video_configuration(
            main={"size": (320, 240)},
            transform=transform  # 여기에서 Transform 설정
        )
        picam2.configure(config) 

        picam2.start()

        stream = io.BytesIO()
        while True:
            stream.seek(0)
            picam2.capture_file(stream, format='jpeg')
            c.frame = stream.getvalue()

            if time.time() - c.start_time > 10:
                break
        picam2.stop()
        c.thread = None
        
app = Flask(__name__)

GPIO.setmode(GPIO.BCM)      

#GPIO 핀 정의
TRIG = 23                                  
ECHO = 24                                  

GPIO.setup(TRIG,GPIO.OUT)                  
GPIO.setup(ECHO,GPIO.IN)

RIGHT_FORWARD = 26                                  
RIGHT_BACKWARD = 19                                   
RIGHT_PWM = 13
LEFT_FORWARD = 21                                  
LEFT_BACKWARD = 20                                   
LEFT_PWM = 16 

GPIO.setup(RIGHT_FORWARD,GPIO.OUT)                  
GPIO.setup(RIGHT_BACKWARD,GPIO.OUT)
GPIO.setup(RIGHT_PWM,GPIO.OUT)
GPIO.output(RIGHT_PWM, 0)
RIGHT_MOTOR = GPIO.PWM(RIGHT_PWM, 100)
RIGHT_MOTOR.start(0)
RIGHT_MOTOR.ChangeDutyCycle(0)

GPIO.setup(LEFT_FORWARD,GPIO.OUT)                  
GPIO.setup(LEFT_BACKWARD,GPIO.OUT)
GPIO.setup(LEFT_PWM,GPIO.OUT)
GPIO.output(LEFT_PWM, 0)
LEFT_MOTOR = GPIO.PWM(LEFT_PWM, 100)
LEFT_MOTOR.start(0)
LEFT_MOTOR.ChangeDutyCycle(0)

#초음파 센서로 거리 측정하는 코드
def getDistance():
  GPIO.output(TRIG, GPIO.LOW)                 
  time.sleep(1)                            

  GPIO.output(TRIG, GPIO.HIGH)                  
  time.sleep(0.00001)                      
  GPIO.output(TRIG, GPIO.LOW)

  while GPIO.input(ECHO)==0:                
    pulse_start = time.time()               
  
  while GPIO.input(ECHO)==1:               
    pulse_end = time.time()                 

  pulse_duration = pulse_end - pulse_start 
  #Multiply pulse duration by 17150 to get distance and round
  distance = pulse_duration * 17150        
  distance = round(distance, 2)           
 
  return distance

#전진, 후진, 펄스 폭 제어에 대한 부분 정의
def rightMotor(forward, backward, pwm):
  GPIO.output(RIGHT_FORWARD,forward)
  GPIO.output(RIGHT_BACKWARD,backward)
  RIGHT_MOTOR.ChangeDutyCycle(pwm)

#전진, 후진, 펄스 폭 제어에 대한 부분 정의
def leftMotor(forward, backward, pwm):
  GPIO.output(LEFT_FORWARD,forward)
  GPIO.output(LEFT_BACKWARD,backward)
  LEFT_MOTOR.ChangeDutyCycle(pwm)

def forward():
    rightMotor(1, 0, 70)
    leftMotor(1, 0, 70)
    time.sleep(1)

def left():
    rightMotor(1, 0, 70) #왼쪽 바퀴가 멈추고 오른쪽이 회전해야 좌회전
    leftMotor(0, 0, 0)
    time.sleep(0.3)

def right():
    rightMotor(0, 0, 0)
    leftMotor(1, 0, 70) #오른쪽 바퀴가 멈추고 왼쪽이 회전해야 우회전
    time.sleep(0.3)

def stop():
    rightMotor(0, 0, 0)
    leftMotor(0, 0, 0)

@app.route("/<command>") #라우팅을 진행
def action(command):
    distance_value = getDistance()
    if command == "F":
        forward()
        message = "Moving Forward"
    elif command == "L":
        left() 
        message = "Turn Left"
    elif command == "R":
        right()   
        message = "Turn Right"  
    else:
        stop()
        message = "Unknown Command [" + command + "] " 

    msg = {
        'message' : message,
        'distance': str(distance_value)
    }
        
    return render_template('video.html', **msg)

def show(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.getStreaming()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n') #프레임을 구별하는 헤더


@app.route('/show')
def showVideo():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(show(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=8300, debug=True, threaded=True)
    except KeyboardInterrupt:
        print ("Terminate program by Keyboard Interrupt")
        GPIO.cleanup()
