groceries =({ "apple", "orange", "banana", "coconut"},
            {"celery", "carrots", "potatoes"},
            {"chicken", "fish", "turkey"})


print(groceries)
for collection in groceries:
    print(collection)
    for food in collection: 
        print(food, end=" ")
    print()
# for collection in groceries:
#     print(collection)
#     for food in collection: 
#         print(food, end=" ")
#     print()


