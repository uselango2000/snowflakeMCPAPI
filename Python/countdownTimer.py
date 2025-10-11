import time
my_time = int(input("Enter the time in sec: "))

for x in range(0, my_time, -1):
    seconds = x %  60
    minutes = int(x /60)
    hours = int(x / 3600)
    print(f"{hours:02}:{minutes:02}:{seconds: 02}")
    print(x)
    time.sleep(1)

print("Times up!!")



