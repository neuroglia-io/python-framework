from dataclasses import dataclass


@dataclass
class Address:
    
    street_name : str
    
    street_number: str
    
    zip_code: str
    
    city : str
    
    state: str
    
    country: str
    
    def __str__(self): return f"{self.street_name} {self.street_number}, {self.zip_code} {self.city}, {self.state}, {self.country}"