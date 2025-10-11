#collection - Single "variable" used to store multiple values
#  List = [] ordered and changeable. Duplicates OK
#  Set  = {} unordered and immutable, but Add/Remove OK. NO duplicates
#  Tuple = () ordered and unchangable. Duplicates OK. FASTER

        
fruits = ["apple", "orange", "banana", "coconut"]
print(dir(fruits))

print(fruits[0]) #prints the first variable
print(fruits[0:3])#prints the first- third set of variables
print(fruits[::2]) #steps

for fruit in fruits:
    print(fruit)
print("apple" in fruits)
print("pinnaple" in fruits)
fruits[0]= "pinnaple"
print(fruit)   # using an index you can reasign a value

fruits.append("pineapple")
fruits.remove("apple")
fruits.insert(0,"pineapple")
fruits.sort()
fruits.reverse()
fruits.clear()
print(fruits.index("apple"))
print(fruits.count("banana"))

fruits= {"apple","orange","banana", "coconut"}

fruits.add("pineapple") 
fruits.remove("apple")
fruits.pop()
fruits.clear()  # no duplicates

print(fruits.index("apple"))
print(fruits.count("banana"))
for fruits in fruits:
    print(fruits)
