# Python compound interest calculator


principle=0
rate = 0
time = 0

while principle < 0:
    principle= float(input("Enter the principle amount: "))
    if principle < 0:
        print("principle can't be less than zero")

while rate < 0:
    rate= float(input("Enter the interest rate: "))
    if rate < 0:
        print("interest rate can't be less than zero")

while time < 0:
    time= float(input("Enter the principle amount: "))
    if time < 0:
        print("Time can't be less zero")

total = principle * pow((1 + rate / 100),time)
print(f"Balance after {time} year/s: ${total:.2f}")
