#!/usr/bin/python
#-*-coding:utf-8 -*-

# 라이브러리 호출
from sense_hat import SenseHat
import time
from time import sleep
from datetime import datetime
import os
import numpy as np
import tensorflow as tf
import tflite_runtime.interpreter as tflite

print(tf.__version__)

long_term   = 4000           # 장기 시간 구간 (샘플)
short_term  = 200            # 단기 시간 구간 (샘플)

acc_dc      = 0.947027769    # 가속도 직류 성분 (초기값)
pressure_dc = 1008.934396561 # 기압 직류 성분 (초기값)

event_threshold_acc = 0.003  # 가속도 이벤트 기준
event_threshold_pre = 0.3    # 기압 이벤트 기준
event_threshold_tem = 50.0   # 온도 이벤트 기준

last_acc = acc_dc            # 최근 이벤트 가속도 값
last_tem = 25                # 최근 이벤트 온도 값
last_pre = pressure_dc       # 최근 이벤트 기압 값

last_acc_tm = 0              # 최근 가속도 이벤트 시각
last_tem_tm = 0              # 최근 온도 이벤트 시각
last_pre_tm = 0              # 최근 기압 이벤트 시각

block_time_acc_sec = 30      # 30초 기간동안 중복 이벤트 생성 차단

light_timer = 0
save_timer  = 4000
first_flag  = True  # 처음 기동하고 초기 안정화 구간까지 저장하지 않기 위해

acc_buffer = [0 for i in range(400)]
pre_buffer = [0 for i in range(400)]

# 센스햇 장치 초기화
sense = SenseHat()
# 속도계 사용 설정
sense.set_imu_config(False, False, True)

# 학습된 모델을 불러온다.
interpreter = tflite.Interpreter(model_path='./model/grandma.tflite')
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

##################################################################################
def save_timer_on():
    global save_timer
    if save_timer > 0:  # 기존에 진행되는 저장 카운터가 있으면 넘어감
      return
    save_timer = short_term    # 200 샘플링 후에 총 400 샘플링을 저장

##################################################################################
# 주파수 공간의 특징 배열을 생성한다.
def feature(acc_buffer):
    fft_buffer = abs( np.fft.fft(acc_buffer) )
    return fft_buffer[5:200]*fft_buffer[5:200]

##################################################################################
# 가속도 배열에서 특징을 추출하여 발걸음 여부를 추정한다.
def is_walk(acc_buffer):
  # 입력 텐서를 정의한다.
  acc_feature = np.array(feature(acc_buffer), dtype=np.float32)
  interpreter.set_tensor(input_details[0]['index'], [acc_feature])
  # 추론을 실시한다.
  interpreter.invoke()
  # 출력 텐서를 처리한다.
  output_data = interpreter.get_tensor(output_details[0]['index'])
  prediction = np.argmax(output_data)
  print("prediction = ", prediction)

  if prediction == 0 : 
    return True
  return False

##################################################################################
# 가속도 이벤트의 계측값을 저장하고, 걸음 이벤트에 대한 로그 기록
def save_event_sample():
    # 계측값 저장
    now = datetime.now()
    max_acc = 0

    filename = "{:%Y%m%d-%H%M%S}".format(now)
    ymd = "{:%Y%m%d}".format(now)
    path = "./event_sample/"+ymd
    if not os.path.isdir(path):                                                           
        os.mkdir(path)
    f = open(path+"/"+filename+".txt", 'w')
    for i in range(400):
      line = "{0} {1}\n".format(acc_buffer[i], pre_buffer[i])
      f.write(line)
      if max_acc < acc_buffer[i]:
        max_acc = acc_buffer[i]
    f.close()

    # 발걸음으로 분류될 경우 기록
    if is_walk(acc_buffer):
      # 발걸음 식별 기록
      filename = "wlk_{:%Y%m%d%H}".format(now)
      event_time = "{:%Y-%m-%d %H:%M:%S}".format(now)
      path = "./event_logs"
      if not os.path.isdir(path):                                                           
          os.mkdir(path)
      f = open(path+"/"+filename+".txt", 'a')
      line = "{0} {1}\n".format(event_time, max_acc)
      f.write(line)
      f.close()

##################################################################################
# 가속도 이벤트 기록
def save_acc_log(acc):
    now = datetime.now()  
    filename = "acc_{:%Y%m%d%H}".format(now)
    event_time = "{:%Y-%m-%d %H:%M:%S}".format(now)
    path = "./event_logs"
    if not os.path.isdir(path):                                                           
        os.mkdir(path)
    f = open(path+"/"+filename+".txt", 'a')
    line = "{0} {1}\n".format(event_time, acc)
    f.write(line)
    f.close()

##################################################################################
# 기압 이벤트 기록
def save_pre_log(pres):
    now = datetime.now()  
    filename = "pre_{:%Y%m%d%H}".format(now)
    event_time = "{:%Y-%m-%d %H:%M:%S}".format(now)
    path = "./event_logs"
    if not os.path.isdir(path):                                                           
        os.mkdir(path)
    f = open(path+"/"+filename+".txt", 'a')
    line = "{0} {1}\n".format(event_time, pres)
    f.write(line)
    f.close()

##################################################################################
# 온도 이벤트 기록
def save_tem_log(tem):
    now = datetime.now()  
    filename = "tem_{:%Y%m%d%H}".format(now)
    event_time = "{:%Y-%m-%d %H:%M:%S}".format(now)
    path = "./event_logs"
    if not os.path.isdir(path):                                                           
        os.mkdir(path)
    f = open(path+"/"+filename+".txt", 'a')
    line = "{0} {1}\n".format(event_time, tem)
    f.write(line)
    f.close()

##################################################################################
# 가속도 이벤트 발생 처리
def event_acc(acc):
    save_timer_on()
    sense.clear(0, 255, 0)  # 초록색 LED 점등
    save_acc_log(acc)

##################################################################################
# 기압 이벤트 발생 처리
def event_pre(pre):
    sense.clear(0, 0, 255)  # 푸른색 LED 점등
    save_pre_log(pre)

##################################################################################
# 온도 이벤트 발생 처리
def event_tem(tem):
    sense.clear(255, 0, 0)  # 붉은색 LED 점등
    save_tem_log(tem)


##################################################################################
# Main
##################################################################################

# LED 준비 신호
sense.clear(255, 255, 255)  # passing in r, g and b values of a colour
sleep(0.5)
sense.clear()  # no arguments defaults to off

#print("Temperature: %s C" % temperature)
#print("Pressure: %s Millibars" % pressure)

while True:
  # 시간, 가속도, 기압(밀리바), 온도(C)
  secs        = time.time()
  acc         = sense.get_accelerometer_raw()
  pressure    = sense.get_pressure()
  temperature = sense.get_temperature()

  for i in range(399):
    acc_buffer[i] = acc_buffer[i+1]
    pre_buffer[i] = pre_buffer[i+1]

  acc_buffer[399] = acc['z'] - acc_dc
  pre_buffer[399] = pressure - pressure_dc

#  str = "{0:.2f} {1:+.9f} {2:+.9f} {3:.1f}".format(secs, acc['z'] - acc_dc, pressure - pressure_dc, temperature)
#  str = "{0:.2f} {1:+.9f}".format(secs, pressure - pressure_dc)
#  print(str)

  if first_flag == False:

    # 가속도 이벤트 탐지
    if abs(acc['z'] - acc_dc) >= event_threshold_acc:
      current_acc = abs(acc['z'] - acc_dc)
      event_acc(current_acc)
      last_acc = current_acc
      last_acc_tm = secs
      light_timer = short_term # 200 샘플

    # 기압 이벤트 탐지
    if abs(pressure - pressure_dc) >= event_threshold_pre:
      current_pre = abs(pressure - pressure_dc)
      if (secs - last_pre_tm > block_time_acc_sec) or (last_pre < current_pre) : # 30초 이내의 중복 이벤트 차단, 더 큰 압력일 때는 이벤트 진행
        event_pre(current_pre)
        last_pre = current_pre
        last_pre_tm = secs
      light_timer = 30

    # 온도 이벤트 탐지
    if temperature >= event_threshold_tem:
      if (secs - last_tem_tm > block_time_acc_sec) or (last_tem < temperature): # 30초 이내의 중복 이벤트 차단, 더 큰 온도일 때는 이벤트 진행
        event_tem(temperature)
        last_tem = temperature
        last_tem_tm = secs
      light_timer = 30

  acc_dc = (acc_dc * long_term + acc['z']) / (long_term + 1)
  pressure_dc = (pressure_dc * long_term + pressure) / (long_term + 1)

  # 정해진 수의 1/100초 후에 LED를 끈다.
  if light_timer > 0:
    if light_timer <= 2:
      sense.clear()
    light_timer = light_timer - 1

  # 정해진 수의 1/100초 후에 샘플을 저장한다.
  if save_timer > 0:
    if save_timer <= 1 and first_flag == False:
      save_event_sample()      
    elif save_timer <= 1 and first_flag == True: # 초기 안정화 기간 종료를 처리한다.
      first_flag = False
    save_timer = save_timer - 1 # 타이머에서 1/100초 감소

    # 테스트 코드 - 자료저장 타미어 진행 표시
    print(save_timer)
