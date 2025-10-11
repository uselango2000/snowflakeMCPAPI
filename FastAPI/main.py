from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()

class Item(BaseModel):
    text: str
    is_done: bool = False

items = []

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/items", response_model=list[Item])
def list_item(limit: int = 10):
    return items[0:limit]

@app.post("/items")
def create_item(item: Item):
    items.append(item)
    print(items)
    return items
    # return {"message": "Item created"}




@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    if item_id  >= len(items):
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    item = items[item_id]
    return item