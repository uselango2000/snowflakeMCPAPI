#logical operators - Evaluate multiple conditions (or, and, Not)
temp= input("Give the temperature of the day: ")
is_possible_for_hazardous_weather= False
possible_for_rain=False
possible_for_high_winds=False
Is_sunny= True 
Is_warm=True
Good_temperature= True 

if 0 < int(temp) < 40 or is_possible_for_hazardous_weather or possible_for_rain or possible_for_high_winds:  
     print("Basketball practice is cancelled today due to bad weather outside in lutz fl")
     print("We will see you at practice next week if the weather is good!")
elif Is_sunny or Is_warm or Good_temperature:
     print("Basketball practice today is still on due to the great weather outside!")
     print("We will see you at practice today at 5pm")
print("Bye have a nice day")
    