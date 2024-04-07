from typing import List, Optional
from pydantic import BaseModel

class Location(BaseModel):
  address1: Optional[str] = None
  address2: Optional[str] = None
  address3: Optional[str] = None
  city: Optional[str] = None
  zip_code: Optional[str] = None
  country: Optional[str] = None
  state: Optional[str] = None
  display_address: List[str] = []

class Coordinates(BaseModel):
  latitude: float
  longitude: float

class Place(BaseModel):
  id: str
  alias: str
  name: str
  image_url: Optional[str] = None
  is_closed: Optional[bool] = None
  url: str
  coordinates: Coordinates
  phone: str
  display_phone: str
  distance: Optional[float] = None
  rating: Optional[float] = None
  review_count: Optional[int] = None
  location: Location
  phone: Optional[str] = None
  price: Optional[str] = None
  categories: Optional[List[dict]] = None
  
  def generate_context(self) -> str:
    context = f"{self.name}\n"
    context += f"Rating: {self.rating} stars for {self.review_count} reviews\n"
    context += f"Location: {' '.join(self.location.display_address)}\n"
    context += f"Phone: {self.display_phone}\n"
    if self.is_closed:
      context += "Currently Closed\n"
      
    return context