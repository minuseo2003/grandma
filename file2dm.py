#!/usr/bin/python
#-*-coding:utf-8 -*-

import time
from time import sleep
from datetime import datetime
from datetime import timedelta
import os
import json
import sys

sys.path.append('./lib')
import message

walk_check_hour  = 8 # 걸음 체크 시간 (시간)
walk_check_limit = 3 # 걸음 체크 시간 (시간)
sleep_start	     = 0 # 수면 시작 시각 (시)
sleep_end        = 6 # 수면 종료 시각 (시)
message_interval = 6 # 재경보 가능 시간

last_walk_messge_sent_datetime = None
last_fire_messge_sent_datetime = None

##################################################################################
# 문자 메시지 전송
def send_message(line):
	data = {
		'messages': [
			{
				'type': 'SMS',
				'to': '수신자전화번호',
				'from': '발신자전화번호',
				'text': line,
			}
		]
	}
	res = message.sendMany(data)
	print(json.dumps(res.json(), indent=2, ensure_ascii=False))

##################################################################################
# 현재 시간을 기준으로 설정된 시간동안 걸음이 탐지된 시간의 수를 확인한다.
def find_walk_log(hours):
	hour_range = hours
	now = datetime.now()
	walk_num = 0
	h = 0
	while(h <= hour_range):
		dh = timedelta(days=0, seconds=h*3600)
		backstep_hour = now - dh
		backstep_hour.hour

		# 수면시간이 들어있을 경우에는 대신 확인시간 영역을 한시간 늘인다.
		if backstep_hour.hour >= sleep_start and backstep_hour.hour <= sleep_end:
			hour_range = hour_range + 1

		# 발걸음 식별 기록
		filename = "wlk_{:%Y%m%d%H}.txt".format(backstep_hour)
		path = "./event_logs/"
		if os.path.isfile(path + filename):
			print(path + "/" + filename)
			walk_num = walk_num + 1			
		h = h + 1

	return walk_num


def check_walk():
	global last_walk_messge_sent_datetime
	global message_interval

	walk_num = find_walk_log(walk_check_hour)
	if walk_num < walk_check_limit:
		message = "[주의] 지난 8시간의 활동시간 동안 할머님의 걸음이 감지된 시간은 " + str(walk_num) + "시간입니다. 확인해보세요."
		if last_walk_messge_sent_datetime == None:
			print(message) # 메시지 출력
			send_message(message)  # 메시지 전송
			last_walk_messge_sent_datetime = datetime.now()
		else:
			now = datetime.now()
			time_gap = now - last_walk_messge_sent_datetime
			dh = timedelta(days=0, seconds=message_interval*3600)

			if time_gap >= dh:
				print(message) # 메시지 출력
				send_message(message)  # 메시지 전송
				last_walk_messge_sent_datetime = now

	print("활동이 존재한 총 시간 : ", walk_num)
	return False

##################################################################################
# 현재 시간을 기준으로 설정된 시간동안 화재 감지 여부를 확인한다.
def find_fire_log(hours):
	hour_range = hours
	now = datetime.now()
	fire_temperature = -1000

	h = 0
	while(h <= hour_range):
		dh = timedelta(days=0, seconds=h*3600)
		backstep_hour = now - dh
		backstep_hour.hour

		# 온도 기록
		filename = "tem_{:%Y%m%d%H}.txt".format(backstep_hour)
		path = "./event_logs/"
		if os.path.isfile(path + filename):
			print(path + "/" + filename)

			f = open(path + "/" + filename, 'r')
			while True:
				line = f.readline()
				if not line: break
				values = line.split(" ")
				a_temperature = float(values[2])
				if a_temperature > fire_temperature :
					fire_temperature = a_temperature
			f.close()
		h = h + 1

	return fire_temperature

def check_fire():
	global last_fire_messge_sent_datetime
	global message_interval

	fire_temperature = find_fire_log(1)

	if fire_temperature > -1000:
		message = "[주의] 최근 " + str(fire_temperature) + "도의 온도가 감지되었습니다. 화재의 우려가 있습니다."

		if last_fire_messge_sent_datetime == None:
			print(message) # 메시지 출력
			send_message(message)  # 메시지 전송
			last_fire_messge_sent_datetime = datetime.now()
		else:
			now = datetime.now()
			time_gap = now - last_fire_messge_sent_datetime
			dh = timedelta(days=0, seconds=3600)

			if time_gap >= dh:
				print(message) # 메시지 출력
				send_message(message)  # 메시지 전송
				last_fire_messge_sent_datetime = now

	return False


##################################################################################
# Main
##################################################################################

# 사람의 장시간 활동 없음, 화재 발생 확인
while(True):
	check_walk()
	check_fire()
	sleep(5)
