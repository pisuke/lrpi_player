import time
from apscheduler.schedulers.background import BackgroundScheduler

def test_scheduler():
   print("TEST")
   print(time.time())

sched = BackgroundScheduler()
sched.add_job(test_scheduler, 'interval', seconds=5)
sched.start(paused=False)

while True:
   pass


