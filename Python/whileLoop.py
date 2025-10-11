# while loop = execute some code WHILE some condition remains True

num = int(input("Enter a # between 1-10: "))


while num < 1 or num > 10:10
print(f"{num} is not valid")
num = int(input("Enter a # between 1-10: "))

print(f"The number you chose was {num}")      