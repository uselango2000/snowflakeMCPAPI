# if = Do some code only IF some condition is True
# else = Do some code only IF some condition is False

# print("Welcome to your local security check,please answer the following questions:")
# name=input("What is your name?: ")
# if name=="Tanish":
#     print("Welcome Tanish! You are allowed to enter.")
# else:
#     print("Sorry, you are not allowed to enter.")
# age=int(input("How old are you?: "))
# if age<11:
#     print("Sorry, you are not allowed to enter.")
# print("Thank you for your cooperation.")


age = int(input("How old are you?: "))

if age >= 100:
    print("You are very old to signup!")
elif age >= 18:
    print("You are allowed to signup!")
elif age < 0:
    print("You are too young to signup!")
else:
    print("You are not allowed to signup!")
    