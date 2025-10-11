#typecasting is the process of converting one data type to another data type
#str() - converts to string
#int() - converts to integer
#float() - converts to float
#bool() - converts to boolean

name = "Tanish" #string
age = 25 #integer
gpa = 6.9#float
isStudent = False#boolean

t = type(age)
print(type(t))
stype = str(age)
print(type(stype))
print(str(isStudent))
print(int(gpa))
print(type(int(gpa)))
print(type(str(isStudent)))